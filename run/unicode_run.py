
from pathlib import Path

from config.config import AnalysisConfig
from src.core.unicode_analyzer import UnicodeAnalyzer
from src.utils.clone_repo import clone_repo
from run.const.repo_list import repo_list

def analyze_unicode(repo_url, extension):
    """
    Clone a repository and analyze the blank space ratio.
    """
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace(".git", "")
    output_dir = Path("analytics") / repo_name / "unicode"
    
    # 1. Configurazione
    config = AnalysisConfig(
        output_format="csv",
        supported_extensions=[extension],
        
        log_file=output_dir / "unicode_analysis.log",
    )
    analyzer = UnicodeAnalyzer(config)

    # 2. Clone repo (if not already cloned)
    repo = clone_repo(repo_url, logger=analyzer.logger)
    if not repo:
        exit(1)
    
    # 3. Analisi
    analyzer.logger.info(f"Inizio analisi del repository {repo_name} con estensione {extension}.")
    analysis_results = analyzer.analyze_repository(repo, extension)

    # 4. Esportazione
    if analysis_results:
        analyzer.export_results(analysis_results, output_dir)

        # Stop logging
        analyzer.logger.info(f"Risultati salvati in: {output_dir}")
        analyzer.logger.handlers.clear()
        
        
if __name__ == "__main__":
    
    for repo_url in repo_list:
        print(f"Analizzando il repository: {repo_url}")
        
        # Analyze orignal repos blank space ratio
        analyze_unicode(
            repo_url=repo_url,
            extension="js",
        )
        
        print(f"Analisi completata per il repository: {repo_url}\n")