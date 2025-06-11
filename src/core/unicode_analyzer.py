import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Any

import homoglyphs as hg
import pandas as pd

from src.core.analyzer import BaseAnalyzer, FileAnalysisResult, TagAnalysisResult
from config.config import AnalysisConfig
from src.utils.clone_repo import clone_repo


class UnicodeAnalyzer(BaseAnalyzer):
    """
    Analizzatore per rilevare caratteri Unicode anomali (omoglifi, caratteri nascosti)
    all'interno di un repository Git.
    """

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """
        Analizza un singolo file per calcolare metriche su caratteri Unicode.

        Calcola il numero totale di caratteri, il numero di omoglifi e il numero
        di caratteri nascosti o di controllo.

        Args:
            file_path: Il percorso del file da analizzare.

        Returns:
            Un'istanza di FileAnalysisResult con i risultati dell'analisi.
        """
        start_time = time.time()
        anomalies = []
        metrics = {
            "total_chars": 0,
            "homoglyph_count": 0,
            "hidden_char_count": 0,
        }

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            metrics["total_chars"] = len(content)

            for char in content:
                # 1. Controllo omoglifi
                try:
                    category = hg.Categories.detect(char)
                    if category not in ['LATIN', 'COMMON']:
                        metrics["homoglyph_count"] += 1
                        anomalies.append({
                            "type": "homoglyph",
                            "char": char,
                            "code": ord(char),
                            "category": category,
                        })
                except Exception:
                    # Ignora errori dalla libreria homoglyphs per caratteri non validi
                    pass

                # 2. Controllo caratteri nascosti o di controllo
                try:
                    category = unicodedata.category(char)
                    if category in ('Cf', 'Cc', 'Cn', 'Co'):
                        metrics["hidden_char_count"] += 1
                        anomalies.append({
                            "type": "hidden/control",
                            "char": char,
                            "code": ord(char),
                            "category": category,
                        })
                except ValueError:
                    # Ignora errori per caratteri di controllo che non hanno una categoria
                    pass
            
            # Calcolo del confidence score basato sulla densità di anomalie
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
            self.logger.error(f"Errore durante l'analisi del file {file_path}: {e}")
            return FileAnalysisResult(
                file_path=str(file_path),
                metrics=metrics,
                anomalies=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                error=str(e),
            )

    def detect_anomalies(self, results: List[FileAnalysisResult]) -> List[Dict[str, Any]]:
        """
        Aggrega le anomalie già rilevate durante l'analisi dei file.

        Args:
            results: Una lista di risultati di analisi di file.

        Returns:
            Una lista aggregata di tutte le anomalie trovate.
        """
        all_anomalies = []
        for res in results:
            if res.anomalies:
                all_anomalies.extend(res.anomalies)
        return all_anomalies

    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path):
        """
        Esporta i risultati dell'analisi Unicode in tre file CSV distinti:
        - total_chars.csv
        - homoglyphs.csv
        - hidden_chars.csv

        Ogni CSV ha i file come righe e i tag come colonne.

        Args:
            results: Un dizionario con i risultati dell'analisi per ogni tag.
            output_dir: La directory dove salvare i file CSV.
        """
        self.logger.info("Costruzione dei DataFrame per l'export in CSV...")
        
        repo_path = Path(next(iter(results.values())).file_results[0].file_path).parent.parent # Stima repo_path

        all_files = set()
        for tag_result in results.values():
            for file_res in tag_result.file_results:
                # Usiamo percorsi relativi per coerenza
                try:
                    relative_path = Path(file_res.file_path).relative_to(repo_path)
                    all_files.add(str(relative_path))
                except ValueError:
                    all_files.add(file_res.file_path)


        if not all_files:
            self.logger.warning("Nessun file analizzato, nessun CSV generato.")
            return
            
        sorted_files = sorted(list(all_files))
        tag_names = list(results.keys())

        # Creazione dei DataFrame
        df_total = pd.DataFrame(index=sorted_files, columns=tag_names)
        df_homoglyphs = pd.DataFrame(index=sorted_files, columns=tag_names)
        df_hidden = pd.DataFrame(index=sorted_files, columns=tag_names)

        # Popolamento dei DataFrame
        for tag_name, tag_result in results.items():
            tag_data = {}
            for file_res in tag_result.file_results:
                try:
                    relative_path = str(Path(file_res.file_path).relative_to(repo_path))
                except ValueError:
                    relative_path = file_res.file_path

                tag_data[relative_path] = file_res.metrics

            df_total[tag_name] = pd.Series({f: m.get('total_chars') for f, m in tag_data.items()})
            df_homoglyphs[tag_name] = pd.Series({f: m.get('homoglyph_count') for f, m in tag_data.items()})
            df_hidden[tag_name] = pd.Series({f: m.get('hidden_char_count') for f, m in tag_data.items()})

        # Gestione dei valori mancanti e salvataggio
        output_files = {
            "total_chars": output_dir / f"{self.__class__.__name__.lower()}_total_chars.csv",
            "homoglyphs": output_dir / f"{self.__class__.__name__.lower()}_homoglyphs.csv",
            "hidden_chars": output_dir / f"{self.__class__.__name__.lower()}_hidden_chars.csv",
        }

        df_total.fillna('').to_csv(output_files["total_chars"])
        df_homoglyphs.fillna('').to_csv(output_files["homoglyphs"])
        df_hidden.fillna('').to_csv(output_files["hidden_chars"])

        self.logger.info("Esportazione CSV completata.")
        for name, path in output_files.items():
            self.logger.info(f" -> File '{name}' salvato in: {path}")
            

# Esempio di utilizzo
if __name__ == '__main__':
    import argparse
    import os
    from config.config import AnalysisConfig
    from src.utils.clone_repo import clone_repo
    
    parser = argparse.ArgumentParser(description="Analizzatore Unicode per repository Git")
    parser.add_argument('repo_url', type=str, help='URL del repository Git da analizzare')
    parser.add_argument("-e", "--extension", required=True, help="Estensione dei file da analizzare (es: py, js)")
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
        max_processes=args.num_processes,
        log_file=output_dir / "unicode_analysis.log",
    )
    
    # 3. Analisi
    analyzer = UnicodeAnalyzer(config)
    analysis_results = analyzer.analyze_repository(repo, args.extension)
    
    # 4. Esportazione
    analyzer.export_results(analysis_results, output_dir)