import os
from dataclasses import dataclass
from typing import List

@dataclass
class AnalysisConfig:
    """Centralized configuration for the analysis."""

    # Directory filters
    filter_dirs: List[str] = None

    # Performance configuration
    max_processes: int = None

    # Output configuration
    output_format: str = "csv"  # Supported: csv, json

    # Supported file extensions
    supported_extensions: List[str] = None

    # Log configuration
    log_file: str = "logs/analysis.log"
    save_log: bool = True

    def __post_init__(self):
        """Sets default values for configurations after initialization."""
        if self.filter_dirs is None:
            self.filter_dirs = [
                ".git", "node_modules", "vendor", "test", "tests",
                "dist", "build", "public", "assets", "bin",
                "coverage", "logs", "temp", "tmp", "packages",
            ]

        if self.max_processes is None:
            # Use a sensible default for parallel processing
            self.max_processes = min(os.cpu_count() or 4, 8)

        if self.supported_extensions is None:
            self.supported_extensions = [
                "py", "js", "ts", "java", "cpp", "c", "h",
                "cs", "go", "rs", "php", "rb", "swift", "kt"
            ]