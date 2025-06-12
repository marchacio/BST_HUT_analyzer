import os
from dataclasses import dataclass
from typing import List

@dataclass
class AnalysisConfig:
    """Configurazione centralizzata per l'analisi"""
    
    # Filtri directory
    filter_dirs: List[str] = None
    
    # Soglie per la detection
    whitespace_threshold_mean: float = 1.0
    whitespace_threshold_previous: float = 1.0
    
    # Configurazione performance
    max_processes: int = None
    
    # Configurazione output
    output_format: str = "csv"  # csv, json
    
    # File extensions supportate
    supported_extensions: List[str] = None
    
    # Log config
    log_file: str = "logs/analysis.log"
    save_log: bool = True
    
    def __post_init__(self):
        if self.filter_dirs is None:
            self.filter_dirs = [
                ".git", "node_modules", "vendor", "test", "tests", 
                "dist", "build", "public", "assets", "bin", 
                "coverage", "logs", "temp", "tmp", 
            ]
        
        if self.max_processes is None:
            self.max_processes = min(os.cpu_count() or 4, 8)
            
        if self.supported_extensions is None:
            self.supported_extensions = [
                "py", "js", "ts", "java", "cpp", "c", "h", 
                "cs", "go", "rs", "php", "rb", "swift", "kt"
            ]

# Esempio di uso:
# config = AnalysisConfig()
# config.to_yaml("config/default_config.yaml")