from git import Repo
import os


def clone_repo(repo_url, repos_dir="repos"):
    """
    Clones a Git repository from the given URL into a local directory.
    This function checks if a local directory named "repos" exists in the relative path
    "../../../repos". If the directory does not exist, it creates it. The function then
    extracts the repository name from the provided URL and clones the repository into
    the "repos" directory if it is not already present. If the repository already exists
    locally, it skips the cloning process.
    
    Args:
        repo_url (str): The URL of the Git repository to clone.
    Returns:
        Repo: An instance of the `Repo` object representing the cloned repository.
    Raises:
        OSError: If there is an issue creating the "repos" directory.
        GitCommandError: If there is an error during the cloning process.
    Note:
        - The function assumes that the `git` command-line tool is installed and
          accessible in the system's PATH.
        - The `.git` suffix in the repository URL is automatically removed if present.
    """
    
    # Crea la cartella "repos" se non esiste
    if not os.path.exists(repos_dir):
        os.makedirs(repos_dir)

    # Estrai il nome del repo dal link
    repo_name = repo_url.rstrip('/').split('/')[-1]
    repo_name = repo_name.split('.git')[0]  # Rimuovi .git se presente
    repo_path = os.path.join(repos_dir, repo_name)

    # Clona il repository se non è già presente
    if not os.path.exists(repo_path):
        print(f"Clonazione di {repo_url}...")
        Repo.clone_from(repo_url, repo_path)
    else:
        print(f"Il repository '{repo_name}' è già presente.")

    print(f"Repository '{repo_name}' clonato con successo in '{repo_path}'.")

    return Repo(repo_path)