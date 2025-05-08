import os
from git import Repo
from src.utils import clone_repo, code_analyzer
import sys

def analyze_repo(repo: Repo):
    try:
        tags = repo.tags
        if len(tags) < 2:
            print("Non ci sono abbastanza tag per identificare le tendenze.")
            return
        
        print(f"Numero di tag trovati: {len(tags)}")

        # Per ogni coppia di tag, salva tutti i commit tra i due tag
        for i in range(len(tags) - 1):
            tag1 = tags[i]
            tag2 = tags[i + 1]
            
            print(f"--Analizzando i commit tra {tag1.name} e {tag2.name}...")
            
            # Take the commits between the two tags
            commits_between_tags = list(
                repo.iter_commits(
                    f"{tag1.name}..{tag2.name}",
                    first_parent=True  # segui solo il primo genitore ai merge
                )
            )
            
            if not commits_between_tags:
                print(f"No commits found between {tag1.name} and {tag2.name}.")
            else:
                for commit in commits_between_tags:
                    code_Data = code_analyzer.code_analyzer_per_commit(commit)
                    
                    if code_Data:
                        print(f"Commit {commit.hexsha}:")
                        print(f"  Funzioni: {code_Data['function_count']}")
                        print(f"  Funzioni asincrone: {code_Data['async_function_count']}")
                        print(f"  Classi: {code_Data['class_count']}")
        
        return 0

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return -1



if __name__ == "__main__":
    
    # Scarica il repository se non è già presente
    repo_url = sys.argv[1] if len(sys.argv) > 1 else None
    if not repo_url:
        raise ValueError("Please provide the repository URL as the first argument.")
    
    repo = clone_repo.clone_repo(repo_url)
        
    analyze_repo(repo)