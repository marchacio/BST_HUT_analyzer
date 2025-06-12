from pathlib import Path

from config.config import AnalysisConfig
from src.core.unicode_analyzer import UnicodeAnalyzer
from src.utils.clone_repo import clone_repo
from run.const.repo_list import repo_list

def analyze_unicode(repo_url, extension):
    """
    Clones a repository and analyzes its Unicode character usage.
    """
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace(".git", "")
    output_dir = Path("analytics") / repo_name / "unicode"
    
    # 1. Configuration
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
    
    # 3. Analysis
    analyzer.logger.info(f"Starting analysis of repository {repo_name} with extension {extension}.")
    analysis_results = analyzer.analyze_repository(repo, extension)

    # 4. Export
    if analysis_results:
        analyzer.export_results(analysis_results, output_dir)

        # Stop logging
        analyzer.logger.info(f"Results saved in: {output_dir}")
        analyzer.logger.handlers.clear()
        
        
if __name__ == "__main__":
    
    for repo_url in repo_list:
        print(f"Analyzing repository: {repo_url}")
        
        # Analyze original repo's Unicode characters
        analyze_unicode(
            repo_url=repo_url,
            extension="js",
        )
        
        print(f"Analysis completed for repository: {repo_url}\n")