import os
import sys
import subprocess
from git import Repo
from matplotlib.backend_bases import MouseEvent
import matplotlib.pyplot as plt

def main():
    if len(sys.argv) != 2:
        print("Uso corretto: python get_github_data.py <link_repo_github>")
        sys.exit(1)

    repo_url = sys.argv[1]
    repos_dir = "repos"

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

    repo = Repo(repo_path)
    
    print(f"Numero totale di tags: {len(repo.tags)}")
    
    # Ottieni il numero totale di commit
    total_commits = sum(1 for _ in repo.iter_commits())
    print(f"Numero totale di commit: {total_commits}")
    
    # crea un grafico tempo/numero commit con matplotlib 
    print("Creazione del grafico dei commit...")
    commit_dates = [commit.committed_datetime for commit in repo.iter_commits()]
    commit_counts = [i + 1 for i in range(len(commit_dates))]

    fig, ax = plt.subplots(figsize=(10, 5))

    # Salva la linea, ma abilita il picker SOLO sui marker (pallini)
    line, = ax.plot(commit_dates, commit_counts, marker='o', linestyle='-', picker=5)

    ax.set_title(f"Numero di commit nel repository {repo_name}")
    ax.set_xlabel("Data di commit")
    ax.set_ylabel("Numero di commit")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Suddividi il grafico con barre verticali per ogni tag
    for tag in repo.tags:
        tag_commit = repo.commit(tag)
        tag_date = tag_commit.committed_datetime
        ax.axvline(x=tag_date, color='r', label=f"Tag: {tag.name}")
        ax.text(tag_date, 0, tag.name, rotation=45, verticalalignment='top', color='red', fontsize=8, transform=ax.get_xaxis_transform())

    # Funzione che viene chiamata quando si clicca su un pallino
    def on_pick(event):
        commitIndex = event.ind[0]
        
        # Ottieni il commit corrispondente al pallino cliccato
        commit = None
        
        # salva il commit
        for c in repo.iter_commits():
            if c.committed_datetime == commit_dates[commitIndex]:
                commit = c
                break
                
        if commit is None:
            print("Commit non trovato.")
            return
        
        # Ottieni il commit corrispondente al pallino cliccato
        print(f"""-----------------------------------------------------------
Commit #{commit_counts[commitIndex]} del {commit_dates[commitIndex]}
{commit.message}
{commit.author}
{commit.stats.files}
-----------------------------------------------------------""")

    # Collega l'evento pick
    fig.canvas.mpl_connect('pick_event', on_pick)

    plt.show()

if __name__ == "__main__":
    main()
