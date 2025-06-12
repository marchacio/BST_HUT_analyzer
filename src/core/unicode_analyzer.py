import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

import homoglyphs as hg
import pandas as pd

from src.core.analyzer import BaseAnalyzer, FileAnalysisResult, TagAnalysisResult
from config.config import AnalysisConfig
from src.utils.clone_repo import clone_repo

# Cache per le categorie dei caratteri per migliorare le performance
_char_category_cache: Dict[str, tuple[str, str]] = {}

# Whitespace characters che non dovrebbero essere considerati sospetti
SAFE_CONTROL_CHARS = {'\n', '\r', '\t', '\f', '\v'}


def get_char_categories_cached(char: str) -> tuple[str, str]:
    """
    Recupera le categorie Unicode e omoglife di un carattere, usando una cache.
    """
    if char not in _char_category_cache:
        try:
            unicode_cat = unicodedata.category(char)
        except TypeError:
            unicode_cat = 'UNKNOWN'
        
        try:
            # La libreria homoglyphs può essere lenta, quindi la mettiamo in cache
            homoglyph_cat = hg.Categories.detect(char)
        except Exception:
            homoglyph_cat = 'UNKNOWN'
            
        _char_category_cache[char] = (unicode_cat, homoglyph_cat)
        
    return _char_category_cache[char]


class UnicodeAnalyzer(BaseAnalyzer):
    """
    Analizzatore per rilevare caratteri Unicode anomali (omoglifi, caratteri nascosti)
    all'interno di un repository Git. Versione ottimizzata.
    """

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """
        Analizza un singolo file per calcolare metriche su caratteri Unicode.
        Questa versione è ottimizzata per analizzare solo i caratteri unici.

        Args:
            file_path: Il percorso del file da analizzare.

        Returns:
            Un'istanza di FileAnalysisResult con i risultati dell'analisi.
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
            
            # Ottimizzazione: conta i caratteri unici invece di analizzare ogni carattere
            char_counts = Counter(content)

            for char, count in char_counts.items():
                unicode_cat, homoglyph_cat = get_char_categories_cached(char)

                # 1. Controllo omoglifi
                if homoglyph_cat not in ('LATIN', 'COMMON', 'UNKNOWN'):
                    metrics["homoglyph_count"] += count
                    anomalies.append({
                        "type": "homoglyph",
                        "char": char,
                        "code": ord(char),
                        "category": homoglyph_cat,
                        "count": count,
                    })

                # 2. Controllo caratteri nascosti o di controllo
                if unicode_cat in ('Cf', 'Cc', 'Cn', 'Co') and char not in SAFE_CONTROL_CHARS:
                    metrics["hidden_char_count"] += count
                    anomalies.append({
                        "type": "hidden/control",
                        "char": char,
                        "code": ord(char),
                        "category": unicode_cat,
                        "count": count,
                    })
            
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
        
        # Stima del percorso base del repository dal primo risultato disponibile
        try:
            repo_path_str = next(iter(results.values())).file_results[0].file_path
            repo_path = Path(repo_path_str).parent.parent
        except (StopIteration, IndexError):
            self.logger.warning("Nessun risultato di file trovato, impossibile determinare il percorso relativo.")
            repo_path = None

        all_files = set()
        for tag_result in results.values():
            for file_res in tag_result.file_results:
                # Usiamo percorsi relativi per coerenza
                try:
                    if repo_path:
                        relative_path = Path(file_res.file_path).relative_to(repo_path)
                        all_files.add(str(relative_path))
                    else:
                        all_files.add(file_res.file_path)
                except ValueError:
                    all_files.add(file_res.file_path)

        if not all_files:
            self.logger.warning("Nessun file analizzato, nessun CSV generato.")
            return
            
        sorted_files = sorted(list(all_files))
        tag_names = list(results.keys())

        # Creazione dei DataFrame
        df_total = pd.DataFrame(index=sorted_files, columns=tag_names, dtype=object)
        df_homoglyphs = pd.DataFrame(index=sorted_files, columns=tag_names, dtype=object)
        df_hidden = pd.DataFrame(index=sorted_files, columns=tag_names, dtype=object)

        # Popolamento dei DataFrame
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

        # Gestione dei valori mancanti e salvataggio
        output_files = {
            "total_chars": output_dir / f"{self.__class__.__name__.lower()}_total_chars.csv",
            "homoglyphs": output_dir / f"{self.__class__.__name__.lower()}_homoglyphs.csv",
            "hidden_chars": output_dir / f"{self.__class__.__name__.lower()}_hidden_chars.csv",
        }
        
        # Usiamo un valore placeholder per i NaN prima di salvare
        df_total.fillna('').to_csv(output_files["total_chars"])
        df_homoglyphs.fillna('').to_csv(output_files["homoglyphs"])
        df_hidden.fillna('').to_csv(output_files["hidden_chars"])

        self.logger.info("Esportazione CSV completata.")
        for name, path in output_files.items():
            self.logger.info(f" -> File '{name}' salvato in: {path}")