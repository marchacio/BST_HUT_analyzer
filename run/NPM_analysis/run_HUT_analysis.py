# npm_hut_analyzer.py

import string
import requests
import tarfile
import io
import os
import time
import confusables
import shutil
import pandas as pd
import multiprocessing as mp
import logging
import ijson
from pathlib import Path
from typing import Dict, List, Optional, Generator, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import Counter  # Importato come da richiesta

# --- CONFIGURATION ---
PACKAGE_FILE = Path("most_popular_packs_22_10_25.json") # Input JSON file
DOWNLOAD_DIR = Path("temp_hut")             # Cartella temporanea (rinominata)
OUTPUT_DIR = Path("npm_hut_results")        # Cartella finale (rinominata)
LOG_FILE = "processed_hut.log"              # File di log (rinominato)
ANALYSIS_EXTENSION = "js"                   # Estensione file da analizzare
MAX_PROCESSES = os.cpu_count() or 1         # Processi per l'analisi
PAUSE_BETWEEN_PACKAGES = 2                  # Pausa tra i pacchetti
PAUSE_BETWEEN_VERSIONS = 0.1                # Pausa tra le versioni

# Cartelle da escludere dall'analisi (come da richiesta)
FILTER_DIRS = {
    "node_modules", ".git", "dist", "build", "test", "tests", 
    "doc", "docs", "example", "examples", "__pycache__", 
    ".vscode", ".github", "benchmark", "benchmarks", "vendor"
}

# --- Setup del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NPM_HUT_Analyzer")

# --- Data Classes (strutture dati) ---
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

# --- Base Analyzer Class (Invariata) ---
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
            self.logger.warning(f"Nessuna cartella di versione trovata in '{package_path}'.")
            return {}

        results = {}
        self.logger.info(f"Analizzando {len(versions)} versioni per '*.{extension}' in '{package_path.name}'.")

        for i, version_path in enumerate(versions):
            version_name = version_path.name
            self.logger.info(f"-> Analizzando versione {version_name} ({i+1}/{len(versions)})...")
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

# --- Implementazione Specific_Analyzer per HUT ---
class UnicodeAnalyzer(BaseAnalyzer):
    
    # Caratteri invisibili e di controllo BiDi [cite: 335]
    INVISIBLE_CHARS: Set[str] = set([
        '\u202A',  # LRE (Left-to-Right Embedding)
        '\u202B',  # RLE (Right-to-Left Embedding)
        '\u202C',  # PDF (Pop Directional Formatting)
        '\u202D',  # LRO (Left-to-Right Override)
        '\u202E',  # RLO (Right-to-Left Override) [cite: 335]
        '\u2066',  # LRI (Left-to-Right Isolate)
        '\u2067',  # RLI (Right-to-Left Isolate)
        '\u2068',  # FSI (First Strong Isolate)
        '\u2069',  # PDI (Pop Directional Isolate)
        '\u200B',  # Zero Width Space
        '\u200C',  # Zero Width Non-Joiner
        '\u200D',  # Zero Width Joiner
        '\uFEFF'   # Zero Width No-Break Space (BOM)
    ])

    def __init__(self, max_processes: int = 1, filter_dirs: Set[str] = set()):
        super().__init__(max_processes)
        
        # Questo set conterrà tutti gli omoglifi, calcolati 
        # dalla libreria 'confusables'
        self.HOMOGLYPHS = set()
        
        LATIN_BASE_CHARS = list(string.ascii_lowercase + string.ascii_uppercase + string.digits)
        # Loop per popolare il set di omoglifi
        for base_char in LATIN_BASE_CHARS:
            # La funzione restituisce il set di omoglifi per quel carattere base
            homoglyph_set = confusables.confusable_characters(base_char)
            self.HOMOGLYPHS.update(homoglyph_set)

        self.HOMOGLYPHS.difference_update(LATIN_BASE_CHARS)  # Rimuovi i caratteri base
        
        # Rimuovi caratteri che non sono lettere/digit, tipo @ o ! o |
        self.HOMOGLYPHS = {ch for ch in self.HOMOGLYPHS if ch.isalnum()}
        
        self.logger.info(f"Totale omoglifi caricati: {len(self.HOMOGLYPHS)}")
                
        self.filter_dirs = filter_dirs
        self.logger.info(f"Filtro cartelle attive: {self.filter_dirs}")

    def _filter_files(self, all_files: List[Path], base_path: Path) -> List[Path]:
        """Filtra i file che si trovano nelle cartelle specificate."""
        filtered_list = []
        for file_path in all_files:
            try:
                # Ottieni le parti del percorso relativo alla cartella della versione
                relative_parts = file_path.relative_to(base_path).parts
                # Controlla se una delle parti del percorso è nell'elenco dei filtri
                if not any(part in self.filter_dirs for part in relative_parts):
                    filtered_list.append(file_path)
                else:
                    self.logger.debug(f"File saltato (filtro): {file_path}")
            except ValueError:
                filtered_list.append(file_path)
        return filtered_list

    def _analyze_version(self, version_path: Path, version_name: str, extension: str) -> TagAnalysisResult:
        """Versione sovrascritta per includere il filtraggio dei file."""
        start_time = time.time()
        all_files = list(version_path.rglob(f"*.{extension}"))
        
        # --- FILTRAGGIO AGGIUNTO ---
        files_to_analyze = self._filter_files(all_files, version_path)
        if len(all_files) > len(files_to_analyze):
            self.logger.info(f"Filtrati {len(all_files) - len(files_to_analyze)} file (es. in /dist, /test).")
        # --- FINE FILTRAGGIO ---

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

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """Analizza un singolo file per caratteri omoglifi e invisibili."""
        start_time = time.time()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content:
                return FileAnalysisResult(str(file_path), {"homoglyph_count": 0, "invisible_count": 0, "total_chars": 0}, [], 1.0, time.time() - start_time)

            # Usa Counter per efficienza, come da tesi 
            char_counts = Counter(content)
            
            homoglyph_count = 0
            invisible_count = 0
            
            # Itera solo sui caratteri UNICI trovati nel file
            for char, count in char_counts.items():
                if char in self.HOMOGLYPHS:
                    self.logger.debug(f"Trovato carattere omoglifo: {char}")
                    homoglyph_count += count
                if char in self.INVISIBLE_CHARS:
                    self.logger.debug(f"Trovato carattere invisibile: {char}")
                    invisible_count += count

            metrics = {
                "homoglyph_count": homoglyph_count, 
                "invisible_count": invisible_count,
                "total_chars": len(content)
            }
            
            return FileAnalysisResult(str(file_path), metrics, [], 1.0, time.time() - start_time)
        except Exception as e:
            self.logger.error(f"Errore durante l'analisi del file {file_path}: {e}")
            return FileAnalysisResult(str(file_path), {}, [], 0.0, time.time() - start_time, str(e))

    def _export_to_csv(self, results: Dict[str, TagAnalysisResult], output_dir: Path, package_name: str):
        """Esporta i risultati HUT (conteggi) in CSV."""
        self.logger.info(f"Esportando i risultati HUT per '{package_name}' in CSV...")
        
        homoglyph_data, invisible_data, total_chars_data = {}, {}, {}
        all_files = set()

        for version_name, version_result in results.items():
            homoglyph_version_data, invisible_version_data, total_chars_version_data = {}, {}, {}
            
            for fr in version_result.file_results:
                # Calcola il percorso relativo basandosi sulla struttura di download
                # temp_hut/express/1.0.0/index.js -> index.js
                relative_path = os.path.join(*Path(fr.file_path).parts[3:])
                if not relative_path: continue
                
                all_files.add(relative_path)
                homoglyph_version_data[relative_path] = fr.metrics.get("homoglyph_count")
                invisible_version_data[relative_path] = fr.metrics.get("invisible_count")
                total_chars_version_data[relative_path] = fr.metrics.get("total_chars")
            
            homoglyph_data[version_name] = homoglyph_version_data
            invisible_data[version_name] = invisible_version_data
            total_chars_data[version_name] = total_chars_version_data

        if not all_files:
            self.logger.warning("Nessun file analizzato. I file CSV saranno vuoti.")
            return

        sorted_files = sorted(list(all_files))
        homoglyph_df = pd.DataFrame(index=sorted_files)
        invisible_df = pd.DataFrame(index=sorted_files)
        total_chars_df = pd.DataFrame(index=sorted_files)

        sorted_versions = sorted(results.keys()) # Ordina le versioni per coerenza

        for version_name in sorted_versions:
            homoglyph_df[version_name] = pd.Series(homoglyph_data.get(version_name, {})).reindex(sorted_files)
            invisible_df[version_name] = pd.Series(invisible_data.get(version_name, {})).reindex(sorted_files)
            total_chars_df[version_name] = pd.Series(total_chars_data.get(version_name, {})).reindex(sorted_files)

        package_output_dir = output_dir / package_name.replace('/', '_')
        package_output_dir.mkdir(exist_ok=True)
        
        homoglyph_output_path = package_output_dir / "homoglyph_count.csv"
        invisible_output_path = package_output_dir / "invisible_count.csv"
        total_chars_output_path = package_output_dir / "total_chars.csv"
        
        homoglyph_df.to_csv(homoglyph_output_path, na_rep='')
        invisible_df.to_csv(invisible_output_path, na_rep='')
        total_chars_df.to_csv(total_chars_output_path, na_rep='')

        self.logger.info(f"Report salvati in: {package_output_dir.resolve()}")

# --- Funzioni Helper (Invariate) ---

def stream_packages_from_file(json_file_path: Path) -> Generator[str, None, None]:
    """
    Legge i nomi dei pacchetti uno per uno da un file JSON di grandi dimensioni.
    Utilizza 'ijson' per efficienza di memoria.
    """
    logger.info(f"Streaming dei nomi dei pacchetti da {json_file_path}...")
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            package_generator = ijson.items(f, 'item')
            for item in package_generator:
                pkg_name = None
                if isinstance(item, dict):
                    pkg_name = item.get("name")
                elif isinstance(item, str):
                    pkg_name = item
                if isinstance(pkg_name, str) and pkg_name.strip():
                    yield pkg_name
                else:
                    logger.debug(f"Saltando entry pacchetto non valida: {item}")
    except FileNotFoundError:
        logger.critical(f"FATALE: File pacchetti non trovato: {json_file_path}")
        return
    except Exception as e:
        logger.critical(f"FATALE: Errore leggendo il file pacchetti {json_file_path}: {e}")
        return

def download_all_versions(package_name: str, package_dir: Path) -> bool:
    """Scarica ed estrae tutte le versioni di un pacchetto."""
    logger.info(f"Recupero metadata per '{package_name}'...")
    try:
        response = requests.get(f"https://registry.npmjs.org/{package_name}", timeout=20)
        response.raise_for_status()
        metadata = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Impossibile recuperare metadata per '{package_name}'. Salto. Dettagli: {e}")
        return False

    versions = metadata.get('versions', {})
    if not versions:
        logger.warning(f"Nessuna versione trovata per '{package_name}'. Salto.")
        return True
    
    logger.info(f"Trovate {len(versions)} versioni. Inizio download in '{package_dir}'...")
    os.makedirs(package_dir, exist_ok=True)

    for version, data in versions.items():
        try:
            tarball_url = data.get('dist', {}).get('tarball')
            if not tarball_url: continue

            version_path = package_dir / version
            if version_path.exists(): continue # Salta se già esiste

            res = requests.get(tarball_url, timeout=30)
            res.raise_for_status()

            with tarfile.open(fileobj=io.BytesIO(res.content), mode="r:gz") as tar:
                for member in tar.getmembers(): # Estrae rimuovendo la cartella 'package/'
                    parts = Path(member.path).parts
                    if len(parts) > 1:
                        member.path = os.path.join(*parts[1:])
                        tar.extract(member, path=version_path)
            time.sleep(PAUSE_BETWEEN_VERSIONS)
        except Exception as e:
            logger.error(f"  Errore sulla versione {version}: {e}")
    return True

def load_processed_packages() -> set:
    if not os.path.exists(LOG_FILE): return set()
    with open(LOG_FILE, 'r') as f: return {line.strip() for line in f}

def mark_package_as_processed(package_name: str):
    with open(LOG_FILE, 'a') as f: f.write(f"{package_name}\n")

# --- MAIN FUNCTION (Modificata per usare UnicodeAnalyzer) ---
def main():
    """Funzione main che orchestra download, analisi e pulizia."""
    processed_packages = load_processed_packages()
    logger.info(f"Trovati {len(processed_packages)} pacchetti già processati nel log.")

    package_stream = stream_packages_from_file(PACKAGE_FILE)
    packages_processed_this_run = 0

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    
    print(f"\n--- Inizio analisi HUT ---")
    print(f"Lettura da: {PACKAGE_FILE.resolve()}")
    print(f"Cartella temporanea: {DOWNLOAD_DIR.resolve()}")
    print(f"Cartella risultati: {OUTPUT_DIR.resolve()}")
    print(f"Cartelle filtrate: {FILTER_DIRS}")
    print(f"Processi usati: {MAX_PROCESSES}\n")
    
    # --- MODIFICA CHIAVE ---
    # Istanzia il nuovo analizzatore passando i filtri
    analyzer = UnicodeAnalyzer(
        max_processes=MAX_PROCESSES, 
        filter_dirs=FILTER_DIRS
    )
    # --- FINE MODIFICA ---

    for package_name in package_stream:
        
        if package_name in processed_packages:
            continue

        packages_processed_this_run += 1
        
        logger.info(f"\n{'='*50}\n"
                    f"[Pacchetto {packages_processed_this_run}] START PACCHETTO: {package_name}"
                    f"\n{'='*50}")
        
        sanitized_name = package_name.replace('/', '_')
        package_path = DOWNLOAD_DIR / sanitized_name
        package_output_dir = OUTPUT_DIR / sanitized_name
        package_output_dir.mkdir(parents=True, exist_ok=True)

        file_handler: Optional[logging.Handler] = None
        try:
            log_file_path = package_output_dir / "log.log"
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            logger.error(f"Impossibile creare file di log per '{package_name}': {e}")
        
        try:
            # 1. DOWNLOAD
            success = download_all_versions(package_name, package_path)
            if not success:
                continue 

            # 2. ANALISI
            results = analyzer.analyze_package_versions(package_path, ANALYSIS_EXTENSION)
            
            # 3. ESPORTAZIONE
            if results:
                analyzer.export_results(results, OUTPUT_DIR, package_name)
            else:
                logger.warning(f"Nessun risultato da esportare per {package_name}.")

            # 4. MARCA COME PROCESSATO
            mark_package_as_processed(package_name)

        except Exception as e:
            logger.critical(f"Errore fatale processando {package_name}: {e}", exc_info=True)
        
        finally:
            # 5. PULIZIA
            if package_path.exists():
                logger.info(f"Pulizia cartella temporanea '{package_path}'...")
                shutil.rmtree(package_path)
                logger.info("Pulizia completata.")
            if file_handler is not None:
                try:
                    logging.getLogger().removeHandler(file_handler)
                    file_handler.close()
                except Exception:
                    pass

            logger.info(f"Attesa di {PAUSE_BETWEEN_PACKAGES} secondi...")
            time.sleep(PAUSE_BETWEEN_PACKAGES)

    logger.info("\n--- Processo completato! ---")

if __name__ == "__main__":
    if os.name != 'posix':
        mp.set_start_method('spawn', force=True)
    main()