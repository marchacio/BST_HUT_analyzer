from pathlib import Path

from config.config import AnalysisConfig
from src.core.unicode_analyzer import UnicodeAnalyzer
from src.utils.clone_repo import clone_repo
from utils.git_manipulators.hut_manipulator import inject_hut_vulnerability
from run.const.repo_list import repo_list

def manipulate_and_analyze_blank_space(repo_url, extension):
    """
    Clones a repository, manipulates it to create a hidden unicode trojan and anlalyze file.
    """
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace(".git", "")
    output_dir = Path("analytics") / repo_name / "manipulated_unicode"

    # 1. Configuration
    config = AnalysisConfig(
        output_format="csv",
        supported_extensions=[extension],
        
        log_file=output_dir / "blank_space_analysis.log",
    )
    analyzer = UnicodeAnalyzer(config)

    # 2. Clone repo (if not already cloned)
    repo = clone_repo(repo_url, logger=analyzer.logger)
    if not repo:
        exit(1)
    
    # 3. Manipulation of the repository
    manipulated_file = inject_hut_vulnerability(
        repo_path=repo.working_tree_dir,
        file_extension=extension,
        filters=config.filter_dirs,
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