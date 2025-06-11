import time
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

    def detect_anomalies(self, results: List[FileAnalysisResult]) -> List[Dict[str, Any]]:
        """
        Metodo richiesto dalla classe base. L'analisi delle anomalie per questo analyzer
        è storica (tra tag) e viene eseguita da `find_historical_deviations`.
        """
        return []

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

    def find_historical_deviations(self, results: Dict[str, TagAnalysisResult]) -> Dict[str, list]:
        """
        Analizza i risultati storici per identificare cambiamenti significativi nel
        blank_space_ratio rispetto alla media e al tag precedente.
        """
        self.logger.info(f"Analisi deviazioni storiche con soglie: Media={self.config.whitespace_threshold_mean}, Precedente={self.config.whitespace_threshold_previous}")

        # 1. Costruire il DataFrame dei rapporti dai risultati
        all_files = set()
        ratio_data = {}
        repo_path = Path(next(iter(results.values())).file_results[0].file_path).parent.parent # Stima repo_path


        for tag_name, tag_result in results.items():
            for fr in tag_result.file_results:
                try:
                    relative_path = Path(fr.file_path).relative_to(repo_path)
                except ValueError:
                    relative_path = Path(fr.file_path)
                all_files.add(str(relative_path))

            ratio_data[tag_name] = {
                str(Path(fr.file_path).relative_to(repo_path)): fr.metrics.get("blank_space_ratio")
                for fr in tag_result.file_results
            }

        if not all_files:
            return {}

        sorted_files = sorted(list(all_files))
        df = pd.DataFrame(index=sorted_files)
        for tag_name in results.keys():
            df[tag_name] = pd.Series(ratio_data.get(tag_name, {})).reindex(sorted_files)

        # 2. Logica di analisi delle deviazioni
        tags = df.columns.tolist()
        if len(tags) < 2:
            self.logger.warning("Meno di due tag trovati. Impossibile calcolare deviazioni storiche.")
            return {}
            
        file_deviations = {}
        for file_path in df.index:
            ratios = pd.to_numeric(df.loc[file_path], errors='coerce')
            
            for i in range(1, len(tags)):
                tag_curr_name = tags[i]
                ratio_curr = ratios.iloc[i]

                if pd.isna(ratio_curr):
                    continue

                # Calcolo deviazione dal precedente
                ratio_prev = ratios.iloc[i-1]
                deviation_from_previous = abs(ratio_curr - ratio_prev) if pd.notna(ratio_prev) else float('inf')

                # Calcolo deviazione dalla media precedente
                previous_ratios_for_mean = ratios.iloc[:i].dropna()
                mean_prev_ratios = previous_ratios_for_mean.mean() if not previous_ratios_for_mean.empty else float('nan')
                deviation_from_mean = abs(ratio_curr - mean_prev_ratios) if pd.notna(mean_prev_ratios) else float('inf')

                if (deviation_from_previous > self.config.whitespace_threshold_previous and 
                    deviation_from_mean > self.config.whitespace_threshold_mean):
                    
                    if file_path not in file_deviations:
                        file_deviations[file_path] = []
                    
                    file_deviations[file_path].append({
                        "tag_current": tag_curr_name,
                        "tag_previous": tags[i-1],
                        "ratio_current": ratio_curr,
                        "ratio_previous": ratio_prev,
                        "mean_previous_ratios": mean_prev_ratios,
                        "deviation_from_previous": deviation_from_previous,
                        "deviation_from_mean": deviation_from_mean,
                    })
        
        self.logger.info(f"Trovati {len(file_deviations)} file con deviazioni significative.")
        return file_deviations

# Esempio di utilizzo
if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Analizza il rapporto spazi bianchi nei file di un repository usando BlankSpaceAnalyzer.")
    parser.add_argument("repo_url", help="URL del repository da analizzare")
    parser.add_argument("-e", "--extension", required=True, help="Estensione dei file da analizzare (es: py, js)")
    parser.add_argument("-sm", "--threshold_mean", type=float, default=1.0, help="Soglia di deviazione dalla media")
    parser.add_argument("-sp", "--threshold_previous", type=float, default=1.0, help="Soglia di deviazione dal precedente")
    parser.add_argument("--num-processes", type=int, default=os.cpu_count(), help="Numero di processi paralleli")
    
    args = parser.parse_args()
    
    # 1. Setup
    repo = clone_repo(args.repo_url)
    if not repo:
        exit(1)
        
    repo_name = args.repo_url.rstrip('/').split('/')[-1].replace(".git", "")
    output_dir = Path("analytics") / repo_name
    
    # 2. Configurazione
    config = AnalysisConfig(
        output_format="csv",
        supported_extensions=[args.extension],
        
        whitespace_threshold_mean= args.threshold_mean,
        whitespace_threshold_previous= args.threshold_previous,
        max_processes=args.num_processes,
        
        log_file=output_dir / "blank_space_analysis.log",
    )

    # 3. Analisi
    analyzer = BlankSpaceAnalyzer(config)
    analysis_results = analyzer.analyze_repository(repo, args.extension)
    
    # 4. Esportazione
    if analysis_results:
        analyzer.export_results(analysis_results, output_dir)

        # 5. Rilevamento Deviazioni Storiche
        deviations = analyzer.find_historical_deviations(analysis_results)
        
        # 6. Report delle deviazioni
        log_path = output_dir / f"{repo_name}_deviation_report.log"
        with open(log_path, 'w') as log_file:
            log_file.write(f"Report Deviazioni per {repo_name}\n")
            log_file.write(f"Soglie: Media > {config.whitespace_threshold_mean}, Precedente > {config.whitespace_threshold_previous}\n\n")
            if not deviations:
                log_file.write("Nessuna deviazione significativa trovata.\n")
            else:
                for file, dev_list in deviations.items():
                    log_file.write(f"--- FILE: {file} ---\n")
                    for dev in dev_list:
                        log_file.write(f"  Anomalia tra tag '{dev['tag_previous']}' e '{dev['tag_current']}'\n")
                        log_file.write(f"    - Rapporto corrente: {dev['ratio_current']:.4f}\n")
                        log_file.write(f"    - Rapporto precedente: {dev['ratio_previous']:.4f}\n")
                        log_file.write(f"    - Deviazione dal precedente: {dev['deviation_from_previous']:.4f}\n")
                        log_file.write(f"    - Media rapporti precedenti: {dev['mean_previous_ratios']:.4f}\n")
                        log_file.write(f"    - Deviazione dalla media: {dev['deviation_from_mean']:.4f}\n\n")
        
        print(f"Analisi completata. Report delle deviazioni salvato in: {log_path}")