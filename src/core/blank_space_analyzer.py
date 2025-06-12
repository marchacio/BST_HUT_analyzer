import time
import math
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

from src.core.analyzer import BaseAnalyzer, FileAnalysisResult, TagAnalysisResult
from config.config import AnalysisConfig
from src.utils.clone_repo import clone_repo

class BlankSpaceAnalyzer(BaseAnalyzer):
    """
    Analyzer per calcolare il rapporto degli spazi bianchi e la lunghezza massima
    delle righe nei file di un repository, identificando deviazioni significative tra i tag.
    """

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """
        Calcola il blank_space_ratio e la lunghezza massima della riga per un singolo file.
        """
        start_time = time.time()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            all_chars = len(content)
            blank_spaces = content.count(' ') + content.count('\t') + content.count('\n') + content.count('\r')
            
            lines = content.splitlines()
            max_line_length = max((len(line) for line in lines), default=0)
            
            ratio = float('inf') if blank_spaces == 0 else all_chars / blank_spaces
            
            metrics = {
                "blank_space_ratio": ratio,
                "max_line_length": max_line_length,
            }

            return FileAnalysisResult(
                file_path=str(file_path),
                metrics=metrics,
                anomalies=[],  # Le anomalie sono rilevate a livello di repository
                confidence_score=1.0,
                processing_time=time.time() - start_time,
                error=None
            )
        except Exception as e:
            self.logger.error(f"Errore durante l'analisi del file {file_path}: {e}")
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
        Esporta i risultati delle metriche `blank_space_ratio` e `max_line_length`
        in due file CSV separati.
        """
        self.logger.info("Esportazione dei risultati di BlankSpaceAnalyzer in CSV...")
        
        ratio_data = {}
        max_line_length_data = {}
        all_files = set()

        repo_path = Path(next(iter(results.values())).file_results[0].file_path).parent.parent # Stima repo_path
        
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
            self.logger.warning("Nessun file analizzato. I file CSV saranno vuoti.")
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

        self.logger.info(f"Report Blank Space Ratio salvato in: {ratio_output_path}")
        self.logger.info(f"Report Max Line Length salvato in: {max_line_output_path}")