from pathlib import Path

from config.config import AnalysisConfig
from src.core.blank_space_analyzer import BlankSpaceAnalyzer
from src.utils.clone_repo import clone_repo
from run.const.repo_list import repo_list

def analyze_blank_space(repo_url, extension, threshold_mean, threshold_previous):
    """
    Clones a repository and analyzes the blank space ratio.
    """
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace(".git", "")
    output_dir = Path("analytics") / repo_name / "original_blank_space"
    
    # 1. Configuration
    config = AnalysisConfig(
        output_format="csv",
        supported_extensions=[extension],
        
        whitespace_threshold_mean=threshold_mean,
        whitespace_threshold_previous=threshold_previous,
        
        log_file=output_dir / "blank_space_analysis.log",
    )
    analyzer = BlankSpaceAnalyzer(config)

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
        
        # Analyze original repo's blank space ratio
        analyze_blank_space(
            repo_url=repo_url,
            extension="js",
            threshold_mean=2.0,
            threshold_previous=2.0
        )
        
        print(f"Analysis completed for repository: {repo_url}\n")