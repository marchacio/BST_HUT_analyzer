import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

import homoglyphs as hg
import pandas as pd

from src.core.analyzer import BaseAnalyzer, FileAnalysisResult, TagAnalysisResult

# Cache for character categories to improve performance
_char_category_cache: Dict[str, tuple[str, str]] = {}

# Whitespace characters that should not be considered suspicious
SAFE_CONTROL_CHARS = {'\n', '\r', '\t', '\f', '\v'}


def get_char_categories_cached(char: str) -> tuple[str, str]:
    """
    Retrieves the Unicode and homoglyph categories of a character, using a cache.
    """
    if char not in _char_category_cache:
        try:
            unicode_cat = unicodedata.category(char)
        except TypeError:
            unicode_cat = 'UNKNOWN'
        
        try:
            # The homoglyphs library can be slow, so we cache it
            homoglyph_cat = hg.Categories.detect(char)
        except Exception:
            homoglyph_cat = 'UNKNOWN'
            
        _char_category_cache[char] = (unicode_cat, homoglyph_cat)
        
    return _char_category_cache[char]


class UnicodeAnalyzer(BaseAnalyzer):
    """
    Analyzer for detecting anomalous Unicode characters (homoglyphs, hidden characters)
    within a Git repository. Optimized version.
    """

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """
        Analyzes a single file to calculate metrics on Unicode characters.
        This version is optimized to analyze only unique characters.

        Args:
            file_path: The path of the file to be analyzed.

        Returns:
            An instance of FileAnalysisResult with the analysis results.
        """
        start_time = time.time()
        anomalies: List[Dict[str, Any]] = []
        metrics = {
            "total_chars": 0,
            "homoglyph_count": 0,
            "hidden_char_count": 0,
        }

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            metrics["total_chars"] = len(content)
            
            # Optimization: count unique characters instead of analyzing every character
            char_counts = Counter(content)

            for char, count in char_counts.items():
                unicode_cat, homoglyph_cat = get_char_categories_cached(char)

                # 1. Homoglyph check
                if homoglyph_cat not in ('LATIN', 'COMMON', 'UNKNOWN'):
                    metrics["homoglyph_count"] += count
                    anomalies.append({
                        "type": "homoglyph",
                        "char": char,
                        "code": ord(char),
                        "category": homoglyph_cat,
                        "count": count,
                    })

                # 2. Hidden or control character check
                if unicode_cat in ('Cf', 'Cc', 'Cn', 'Co') and char not in SAFE_CONTROL_CHARS:
                    metrics["hidden_char_count"] += count
                    anomalies.append({
                        "type": "hidden/control",
                        "char": char,
                        "code": ord(char),
                        "category": unicode_cat,
                        "count": count,
                    })
            
            # Calculate confidence score based on anomaly density
            total_anomalies = metrics["homoglyph_count"] + metrics["hidden_char_count"]
            if metrics["total_chars"] > 0 and total_anomalies > 0:
                confidence = min(1.0, total_anomalies / metrics["total_chars"] * 100)
            else:
                confidence = 0.0

            return FileAnalysisResult(
                file_path=str(file_path),
                metrics=metrics,
                anomalies=anomalies,
                confidence_score=confidence,
                processing_time=time.time() - start_time,
                error=None,
            )

        except Exception as e:
            self.logger.error(f"Error while analyzing file {file_path}: {e}")
            return FileAnalysisResult(
                file_path=str(file_path),
                metrics=metrics,
                anomalies=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                error=str(e),
            )

    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path):
        """
        Exports the Unicode analysis results into three distinct CSV files:
        - total_chars.csv
        - homoglyphs.csv
        - hidden_chars.csv

        Each CSV has files as rows and tags as columns.

        Args:
            results: A dictionary with the analysis results for each tag.
            output_dir: The directory where to save the CSV files.
        """
        self.logger.info("Building DataFrames for CSV export...")
        
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

        all_files = set()
        for tag_result in results.values():
            for file_res in tag_result.file_results:
                # Use relative paths for consistency
                try:
                    if repo_path:
                        relative_path = Path(file_res.file_path).relative_to(repo_path)
                        all_files.add(str(relative_path))
                    else:
                        all_files.add(file_res.file_path)
                except ValueError:
                    all_files.add(file_res.file_path)

        if not all_files:
            self.logger.warning("No files analyzed, no CSVs generated.")
            return
            
        sorted_files = sorted(list(all_files))
        tag_names = list(results.keys())

        # Create DataFrames
        df_total = pd.DataFrame(index=sorted_files, columns=tag_names, dtype=object)
        df_homoglyphs = pd.DataFrame(index=sorted_files, columns=tag_names, dtype=object)
        df_hidden = pd.DataFrame(index=sorted_files, columns=tag_names, dtype=object)

        # Populate DataFrames
        for tag_name, tag_result in results.items():
            for file_res in tag_result.file_results:
                try:
                    if repo_path:
                        relative_path = str(Path(file_res.file_path).relative_to(repo_path))
                    else:
                        relative_path = file_res.file_path
                except ValueError:
                    relative_path = file_res.file_path

                if relative_path in sorted_files:
                    df_total.loc[relative_path, tag_name] = file_res.metrics.get('total_chars')
                    df_homoglyphs.loc[relative_path, tag_name] = file_res.metrics.get('homoglyph_count')
                    df_hidden.loc[relative_path, tag_name] = file_res.metrics.get('hidden_char_count')

        # Handle missing values and save
        output_files = {
            "total_chars": output_dir / f"{self.__class__.__name__.lower()}_total_chars.csv",
            "homoglyphs": output_dir / f"{self.__class__.__name__.lower()}_homoglyphs.csv",
            "hidden_chars": output_dir / f"{self.__class__.__name__.lower()}_hidden_chars.csv",
        }
        
        # Use a placeholder value for NaNs before saving
        df_total.fillna('').to_csv(output_files["total_chars"])
        df_homoglyphs.fillna('').to_csv(output_files["homoglyphs"])
        df_hidden.fillna('').to_csv(output_files["hidden_chars"])

        self.logger.info("CSV export completed.")
        for name, path in output_files.items():
            self.logger.info(f" -> File '{name}' saved to: {path}")