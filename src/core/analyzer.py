from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
from git import Repo
from logging import Logger

from config.config import AnalysisConfig
from src.utils.log import init_logging

@dataclass
class FileAnalysisResult:
    """Result of the analysis of a single file."""
    file_path: str
    metrics: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    confidence_score: float
    processing_time: float
    error: Optional[str] = None

@dataclass
class TagAnalysisResult:
    """Result of the analysis of a tag."""
    tag_name: str
    files_analyzed: int
    total_anomalies: int
    high_confidence_anomalies: int
    processing_time: float
    file_results: List[FileAnalysisResult]

class BaseAnalyzer(ABC):
    """Abstract base class for all analyzers."""
    
    def __init__(self, config: 'AnalysisConfig'):
        self.config = config
        self.logger = self._setup_logger()
        self._results_cache = {}
    
    def _setup_logger(self) -> Logger:
        """Set up a custom logger."""
        return init_logging(
            log_file=self.config.log_file,
            save_file=self.config.save_log,
        )
    
    @abstractmethod
    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """Analyzes a single file."""
        pass
    
    def analyze_repository(self, repo: Repo, extension: str) -> Dict[str, TagAnalysisResult]:
        """Analyzes the entire repository across all tags."""
        repo_path = Path(repo.working_tree_dir)
        tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
        
        if not tags:
            self.logger.warning("No tags found in the repository.")
            return {}
        
        results = {}
        self.logger.info(f"Analyzing {len(tags)} tags for extension '{extension}'.")
        
        for i, tag in enumerate(tags):
            self.logger.info(f"Analyzing tag {tag.name} ({i+1}/{len(tags)}).")
            
            try:
                repo.git.checkout(tag.commit, force=True)
                tag_result = self._analyze_tag(repo_path, tag.name, extension)
                results[tag.name] = tag_result
                
            except Exception as e:
                self.logger.error(f"Error analyzing tag {tag.name}: {e}.")
                continue
        
        return results
    
    def _analyze_tag(self, repo_path: Path, tag_name: str, extension: str) -> TagAnalysisResult:
        """Analyzes all files for a specific tag."""
        import time
        start_time = time.time()
        
        files_to_analyze = self._get_files_for_extension(repo_path, extension)
        file_results = []
        
        # Parallel analysis if configured
        if self.config.max_processes > 1:
            file_results = self._analyze_files_parallel(files_to_analyze)
        else:
            file_results = self._analyze_files_sequential(files_to_analyze)
        
        # Filter valid results
        valid_results = [r for r in file_results if r.error is None]
        
        # Calculate statistics
        total_anomalies = sum(len(r.anomalies) for r in valid_results)
        high_confidence = sum(1 for r in valid_results 
                              if r.confidence_score > 0.7 and r.anomalies)
        
        processing_time = time.time() - start_time
        
        return TagAnalysisResult(
            tag_name=tag_name,
            files_analyzed=len(valid_results),
            total_anomalies=total_anomalies,
            high_confidence_anomalies=high_confidence,
            processing_time=processing_time,
            file_results=valid_results
        )
    
    def _get_files_for_extension(self, repo_path: Path, extension: str) -> List[Path]:
        """Collects all files with the specified extension."""
        files = []
        
        for file_path in repo_path.rglob(f"*.{extension}"):
            # Skip filtered directories
            if any(filter_dir in file_path.parts for filter_dir in self.config.filter_dirs):
                continue
            
            if file_path.is_file(): # avoid directories with the extension at the end 
                files.append(file_path)
        
        return files
    
    def _analyze_files_sequential(self, files: List[Path]) -> List[FileAnalysisResult]:
        """Sequential analysis of files."""
        return [self.analyze_file(f) for f in files]
    
    def _analyze_files_parallel(self, files: List[Path]) -> List[FileAnalysisResult]:
        """Parallel analysis of files."""
        import multiprocessing as mp
        
        with mp.Pool(processes=self.config.max_processes) as pool:
            return pool.map(self.analyze_file, files)
    
    def export_results(self, results: Dict[str, TagAnalysisResult], 
                       output_dir: Path):
        """Exports the results in various formats."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config.output_format == "csv":
            self._export_to_csv(results, output_dir)
        elif self.config.output_format == "json":
            self._export_to_json(results, output_dir)
        else:
            raise ValueError(f"Format '{self.config.output_format}' not supported.")
    
    @abstractmethod
    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path):
        """Specific implementation for CSV export."""
        pass
    
    def _export_to_json(self, results: Dict[str, TagAnalysisResult], output_dir: Path):
        """Generic JSON export."""
        import json
        from dataclasses import asdict
        
        json_data = {tag: asdict(result) for tag, result in results.items()}
        
        output_file = output_dir / f"{self.__class__.__name__.lower()}_results.json"
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        self.logger.info(f"Results exported to: {output_file}")