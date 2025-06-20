import time
import pandas as pd
from pathlib import Path
from typing import Dict

from src.core.analyzer import BaseAnalyzer, FileAnalysisResult, TagAnalysisResult

class BlankSpaceAnalyzer(BaseAnalyzer):
    """
    Analyzer to calculate the whitespace ratio and maximum line length
    in repository files, identifying significant deviations between tags.
    """

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """
        Calculates the blank_space_ratio and maximum line length for a single file.
        """
        start_time = time.time()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            blank_spaces = content.count(' ') + content.count('\t') + content.count('\n') + content.count('\r')
            all_chars = len(content) - blank_spaces  # exclude blank spaces from total character count
            
            lines = content.splitlines()
            max_line_length = max((len(line) for line in lines), default=0)
            
            ratio = float('inf') if all_chars == 0 else blank_spaces / all_chars
            
            metrics = {
                "blank_space_ratio": ratio,
                "max_line_length": max_line_length,
            }

            return FileAnalysisResult(
                file_path=str(file_path),
                metrics=metrics,
                anomalies=[],  # Anomalies are detected at the repository level
                confidence_score=1.0,
                processing_time=time.time() - start_time,
                error=None
            )
        except Exception as e:
            self.logger.error(f"Error while analyzing file {file_path}: {e}")
            return FileAnalysisResult(
                file_path=str(file_path),
                metrics={},
                anomalies=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                error=str(e)
            )

    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path):
        """
        Exports the `blank_space_ratio` and `max_line_length` metrics results
        into two separate CSV files.
        """
        self.logger.info("Exporting BlankSpaceAnalyzer results to CSV...")
        
        ratio_data = {}
        max_line_length_data = {}
        all_files = set()

        # Estimate repo_path
        repo_path = None
        # Search for the first TagAnalysisResult that actually has files
        for tag_result in results.values():
            if tag_result.file_results:
                repo_path = Path(tag_result.file_results[0].file_path).parent.parent
                break

        if repo_path is None:
            self.logger.warning("No files were found in any tag. Cannot determine repository path. CSV files will be empty.")
            return
        
        for tag_name, tag_result in results.items():
            ratio_tag_data = {}
            max_line_length_tag_data = {}
            for fr in tag_result.file_results:
                try:
                    relative_path = Path(fr.file_path).relative_to(repo_path)
                except ValueError:
                    relative_path = Path(fr.file_path) # Fallback

                all_files.add(str(relative_path))
                ratio_tag_data[str(relative_path)] = fr.metrics.get("blank_space_ratio")
                max_line_length_tag_data[str(relative_path)] = fr.metrics.get("max_line_length")
            
            ratio_data[tag_name] = ratio_tag_data
            max_line_length_data[tag_name] = max_line_length_tag_data

        if not all_files:
            self.logger.warning("No files analyzed. The CSV files will be empty.")
            return

        sorted_files = sorted(list(all_files))
        
        ratio_df = pd.DataFrame(index=sorted_files)
        max_line_length_df = pd.DataFrame(index=sorted_files)

        for tag_name in results.keys():
            ratio_df[tag_name] = pd.Series(ratio_data.get(tag_name, {})).reindex(sorted_files)
            max_line_length_df[tag_name] = pd.Series(max_line_length_data.get(tag_name, {})).reindex(sorted_files)

        ratio_output_path = output_dir / f"blank_space_ratio.csv"
        max_line_output_path = output_dir / f"blank_space_max_line_length.csv"
        
        ratio_df.to_csv(ratio_output_path, na_rep='')
        max_line_length_df.to_csv(max_line_output_path, na_rep='')

        self.logger.info(f"Blank Space Ratio report saved to: {ratio_output_path}")
        self.logger.info(f"Max Line Length report saved to: {max_line_output_path}")