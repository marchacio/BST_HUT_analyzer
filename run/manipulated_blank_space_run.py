from pathlib import Path

from config.config import AnalysisConfig
from src.core.blank_space_analyzer import BlankSpaceAnalyzer
from src.utils.clone_repo import clone_repo
from src.utils.git_manipulator import perform_local_git_manipulation
from run.const.repo_list import repo_list

def manipulate_and_analyze_blank_space(repo_url, extension, threshold_mean, threshold_previous):
    """
    Clones a repository, manipulates it to create a blank space trojan, and analyzes the blank space ratio.
    """
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace(".git", "")
    output_dir = Path("analytics") / repo_name / "manipulated_blank_space"

    # 1. Configuration
    config = AnalysisConfig(
        output_format="csv",
        supported_extensions=[extension],
        
        log_file=output_dir / "blank_space_analysis.log",
    )
    analyzer = BlankSpaceAnalyzer(config)

    # 2. Clone repo (if not already cloned)
    repo = clone_repo(repo_url, logger=analyzer.logger)
    if not repo:
        exit(1)
    
    # 3. Manipulation of the repository
    manipulated_file = perform_local_git_manipulation(
        repo_path=repo.working_tree_dir,
        file_extension=extension,
        filters=config.filter_dirs,
        n_blank_chars=800  # Example value, adjust as needed
    )

    # 4. Analysis
    analyzer.logger.info(f"Starting analysis of repository {repo_name} with extension {extension}.\nManipulated file: {manipulated_file}")
    analysis_results = analyzer.analyze_repository(repo, extension)

    # 5. Export
    if analysis_results:
        analyzer.export_results(analysis_results, output_dir)
        
        # Stop logging
        analyzer.logger.info(f"Results saved in: {output_dir}")
        analyzer.logger.handlers.clear()
        
        
if __name__ == "__main__":
    
    for repo_url in repo_list:
        print(f"Analyzing repository: {repo_url}")
        
        # Manipulate and analyze the blank space ratio
        manipulate_and_analyze_blank_space(
            repo_url=repo_url,
            extension="js",
            threshold_mean=3.5,
            threshold_previous=3.5
        )
        
        print(f"Analysis completed for repository: {repo_url}\n")