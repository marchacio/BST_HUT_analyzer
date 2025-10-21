# npm_full_analyzer.py

import requests
import tarfile
import io
import os
import time
import shutil
import pandas as pd
import multiprocessing as mp
import logging
from pathlib import Path
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# --- CONFIGURATION ---
#PACKAGES_TO_FETCH = 50000
PACKAGES_TO_FETCH = 10000                   # Number of packages to analyze
DOWNLOAD_DIR = Path("temp")              # Temporary folder for the current package
OUTPUT_DIR = Path("npm_results")         # Final folder for CSV results
LOG_FILE = "processed.log"               # File to resume the process
ANALYSIS_EXTENSION = "js"                # File extension to analyze
MAX_PROCESSES = os.cpu_count() or 1      # Processes for analysis (use 1 for debugging)
PAUSE_BETWEEN_PACKAGES = 2               # Pause in seconds between packages
PAUSE_BETWEEN_VERSIONS = 0.1             # Pause during version downloads

# --- Setup del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NPM_Analyzer")

# --- Data Classes (data structures) ---
@dataclass
class FileAnalysisResult:
    file_path: str
    metrics: Dict
    anomalies: List[str]
    confidence_score: float
    processing_time: float
    error: str | None = None

@dataclass
class TagAnalysisResult:
    tag_name: str
    files_analyzed: int
    processing_time: float
    file_results: List[FileAnalysisResult] = field(default_factory=list)

# --- Base Analyzer Class ---
class BaseAnalyzer(ABC):
    def __init__(self, max_processes: int = 1):
        self.max_processes = max_processes
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        pass

    def analyze_package_versions(self, package_path: Path, extension: str) -> Dict[str, TagAnalysisResult]:
        versions = sorted([d for d in package_path.iterdir() if d.is_dir()])
        if not versions:
            self.logger.warning(f"No version folders found in '{package_path}'.")
            return {}

        results = {}
        self.logger.info(f"Analyzing {len(versions)} versions for '*.{extension}' in '{package_path.name}'.")

        for i, version_path in enumerate(versions):
            version_name = version_path.name
            self.logger.info(f"-> Analyzing version {version_name} ({i+1}/{len(versions)})...")
            results[version_name] = self._analyze_version(version_path, version_name, extension)
        
        return results

    def _analyze_version(self, version_path: Path, version_name: str, extension: str) -> TagAnalysisResult:
        start_time = time.time()
        files_to_analyze = list(version_path.rglob(f"*.{extension}"))
        
        if not files_to_analyze:
            return TagAnalysisResult(version_name, 0, time.time() - start_time, [])

        if self.max_processes > 1 and len(files_to_analyze) > 1:
            with mp.Pool(processes=self.max_processes) as pool:
                file_results = pool.map(self.analyze_file, files_to_analyze)
        else:
            file_results = [self.analyze_file(f) for f in files_to_analyze]

        valid_results = [r for r in file_results if r.error is None]
        
        return TagAnalysisResult(
            tag_name=version_name,
            files_analyzed=len(valid_results),
            processing_time=time.time() - start_time,
            file_results=valid_results
        )
    
    def export_results(self, results: Dict[str, TagAnalysisResult], output_dir: Path, package_name: str):
        output_dir.mkdir(parents=True, exist_ok=True)
        self._export_to_csv(results, output_dir, package_name)

    @abstractmethod
    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path, package_name: str):
        pass

# --- Specific Analyzer Implementation ---
class BlankSpaceAnalyzer(BaseAnalyzer):
    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        start_time = time.time()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            blank_spaces = content.count(' ') + content.count('\t') + content.count('\n') + content.count('\r')
            total_chars = len(content)
            lines = content.splitlines()
            max_line_length = max((len(line) for line in lines), default=0)
            ratio = float('inf') if total_chars == 0 else blank_spaces / total_chars
            
            metrics = {"blank_space_ratio": ratio, "max_line_length": max_line_length}
            return FileAnalysisResult(str(file_path), metrics, [], 1.0, time.time() - start_time)
        except Exception as e:
            self.logger.error(f"Error while analyzing file {file_path}: {e}")
            return FileAnalysisResult(str(file_path), {}, [], 0.0, time.time() - start_time, str(e))

    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path, package_name: str):
        self.logger.info(f"Exporting results for '{package_name}' to CSV...")
        
        ratio_data, max_line_length_data, all_files = {}, {}, set()

        for version_name, version_result in results.items():
            ratio_version_data, max_line_length_version_data = {}, {}
            
            for fr in version_result.file_results:
                # The relative path is computed abstractly, not depending on the base folder
                # e.g. /temp/express/1.0.0/index.js -> index.js
                relative_path = os.path.join(*Path(fr.file_path).parts[3:])
                
                all_files.add(relative_path)
                ratio_version_data[relative_path] = fr.metrics.get("blank_space_ratio")
                max_line_length_version_data[relative_path] = fr.metrics.get("max_line_length")
            
            ratio_data[version_name] = ratio_version_data
            max_line_length_data[version_name] = max_line_length_version_data

        if not all_files:
            self.logger.warning("No files analyzed. CSV files will be empty.")
            return

        sorted_files = sorted(list(all_files))
        ratio_df = pd.DataFrame(index=sorted_files)
        max_line_length_df = pd.DataFrame(index=sorted_files)

        for version_name in sorted(results.keys()): # Sort versions for consistency
            ratio_df[version_name] = pd.Series(ratio_data.get(version_name, {})).reindex(sorted_files)
            max_line_length_df[version_name] = pd.Series(max_line_length_data.get(version_name, {})).reindex(sorted_files)

        package_output_dir = output_dir / package_name.replace('/', '_')
        package_output_dir.mkdir(exist_ok=True)
        
        ratio_output_path = package_output_dir / "blank_space_ratio.csv"
        max_line_output_path = package_output_dir / "blank_space_max_line_length.csv"
        
        ratio_df.to_csv(ratio_output_path, na_rep='')
        max_line_length_df.to_csv(max_line_output_path, na_rep='')

        self.logger.info(f"Reports saved in: {package_output_dir.resolve()}")

def get_top_packages(limit=100, startFrom=0) -> List[str]:
    """Retrieve the names of the most popular packages from the NPM API."""
    packages, page_size = [], 250
    logger.info(f"Fetching the top {limit} package names starting from {startFrom}...")
    for i in range(startFrom, limit, page_size):
        print(f"Fetching packages {i} to {min(i+page_size, limit)}...")
        try:
            params = {'text': 'boost-exact:false', 'popularity': 1.0, 'size': page_size, 'from': i}
            response = requests.get("https://registry.npmjs.org/-/v1/search", params=params, timeout=20)
            response.raise_for_status()
            for obj in response.json().get('objects', []):
                packages.append(obj['package']['name'])
                if len(packages) >= limit: break
            logger.info(f"  Retrieved {startFrom+len(packages)}/{limit} package names...")
            time.sleep(0.5)
            if len(packages) >= limit: break
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching package list: {e}")
            break
    logger.info(f"Fetch completed. Found {len(packages)} packages.")
    return packages

def download_all_versions(package_name: str, package_dir: Path) -> bool:
    """Download and extract all versions of a package."""
    logger.info(f"Fetching metadata for '{package_name}'...")
    try:
        response = requests.get(f"https://registry.npmjs.org/{package_name}", timeout=20)
        response.raise_for_status()
        metadata = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Unable to fetch metadata for '{package_name}'. Skipping. Details: {e}")
        return False

    versions = metadata.get('versions', {})
    if not versions:
        logger.warning(f"No versions found for '{package_name}'. Skipping.")
        return True
    
    logger.info(f"Found {len(versions)} versions. Starting download into '{package_dir}'...")
    os.makedirs(package_dir, exist_ok=True)

    for version, data in versions.items():
        try:
            tarball_url = data.get('dist', {}).get('tarball')
            if not tarball_url: continue

            version_path = package_dir / version
            if version_path.exists(): continue # Skip if already exists

            res = requests.get(tarball_url, timeout=30)
            res.raise_for_status()

            with tarfile.open(fileobj=io.BytesIO(res.content), mode="r:gz") as tar:
                for member in tar.getmembers(): # Extract removing the 'package/' folder
                    parts = Path(member.path).parts
                    if len(parts) > 1:
                        member.path = os.path.join(*parts[1:])
                        tar.extract(member, path=version_path)
            time.sleep(PAUSE_BETWEEN_VERSIONS)
        except Exception as e:
            logger.error(f"  Error on version {version}: {e}")
    return True

def load_processed_packages() -> set:
    if not os.path.exists(LOG_FILE): return set()
    with open(LOG_FILE, 'r') as f: return {line.strip() for line in f}

def mark_package_as_processed(package_name: str):
    with open(LOG_FILE, 'a') as f: f.write(f"{package_name}\n")

def main():
    """Main function that orchestrates download, analysis and cleanup."""
    processed_packages = load_processed_packages()
    logger.info(f"Found {len(processed_packages)} packages already processed in the log.")
    
    all_packages = get_top_packages(
        limit=PACKAGES_TO_FETCH, 
        startFrom=len(processed_packages)
    )
    logger.info(f"Total packages fetched: {len(all_packages)}")
    logger.info(f"Packages already processed: {len(processed_packages)}")
    packages_to_run = [p for p in all_packages if p not in processed_packages]
    logger.info(f"Total packages to process: {len(packages_to_run)}")

    if not packages_to_run:
        logger.info("All requested packages have already been processed. Exiting.")
        return

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    
    print(f"\n--- Starting analysis of {len(packages_to_run)} packages ---\n")
    print(f"Temporary folder: {DOWNLOAD_DIR.resolve()}")
    print(f"Results folder: {OUTPUT_DIR.resolve()}")
    print(f"Processes used: {MAX_PROCESSES}\n")
    
    analyzer = BlankSpaceAnalyzer(max_processes=MAX_PROCESSES)

    for i, package_name in enumerate(packages_to_run):
        logger.info(f"\n{'='*50}\n[{i+1}/{len(packages_to_run)}] START PACKAGE: {package_name}\n{'='*50}")
        
        # Define a unique path for the current package
        sanitized_name = package_name.replace('/', '_')
        package_path = DOWNLOAD_DIR / sanitized_name
        package_output_dir = OUTPUT_DIR / sanitized_name
        package_output_dir.mkdir(parents=True, exist_ok=True)

        # Setup per-package file logger
        file_handler: Optional[logging.Handler] = None
        try:
            log_file_path = package_output_dir / "log.log"
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            # Attach to root logger so all loggers propagate here
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            logger.error(f"Unable to create log file for '{package_name}': {e}")
        
        try:
            # 1. DOWNLOAD
            success = download_all_versions(package_name, package_path)
            if not success:
                continue # Skip to next package if download fails

            # 2. ANALYSIS
            results = analyzer.analyze_package_versions(package_path, ANALYSIS_EXTENSION)
            
            # 3. EXPORT
            if results:
                analyzer.export_results(results, OUTPUT_DIR, package_name)
            else:
                logger.warning(f"No results to export for {package_name}.")

            # 4. MARK AS PROCESSED
            mark_package_as_processed(package_name)

        except Exception as e:
            logger.critical(f"Fatal error while processing {package_name}: {e}", exc_info=True)
        
        finally:
            # 5. CLEANUP (always executed, even on error)
            if package_path.exists():
                logger.info(f"Cleaning temporary folder '{package_path}'...")
                shutil.rmtree(package_path)
                logger.info("Cleanup completed.")
            # Remove and close the package-specific file handler (if present)
            if file_handler is not None:
                try:
                    logging.getLogger().removeHandler(file_handler)
                    file_handler.close()
                except Exception:
                    pass

            logger.info(f"Waiting {PAUSE_BETWEEN_PACKAGES} seconds...")
            time.sleep(PAUSE_BETWEEN_PACKAGES)

    logger.info("\n--- Process completed! ---")

if __name__ == "__main__":
    # Su Windows/macOS, il metodo di avvio di default per multiprocessing può causare problemi
    # se lo script non è strutturato correttamente. Impostarlo a 'fork' o 'spawn' può aiutare.
    if os.name != 'posix': # Non è un sistema Unix-like (es. Windows)
        mp.set_start_method('spawn', force=True)
    main()