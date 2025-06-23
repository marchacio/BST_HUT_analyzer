# BST and HUT Vulnerabilities Analyzer

This repository contains scripts to test the HUT (Hidden Unicode Trick) and BST (Blank Space Trick) vulnerabilities.

Check my [study](TODO) for more information about these vulnerabilities.


## Run Tests
To run the tests, you need to have Python 3 installed on your system.

Each following command will download the dataset (if not downloaded yet), manipulate it (if necessary) and get the results.

### HUT Vulnerabilities Dataset
To test the dataset of repos specified in the `/run/const/repo_list.py` 
file, run the following commands (in this order):
```bash 
python3 -m run.original_unicode_run     # This will test the original repos
python3 -m run.manipulated_unicode_run  # This will inject HUT vulnerability and test the repos
```

### BST Vulnerabilities Dataset
To test the dataset of repos specified in the `/run/const/repo_list.py`
file, run the following commands (in this order):
```bash 
python3 -m run.original_blank_space_run     # This will test the original repos
python3 -m run.manipulated_blank_space_run  # This will inject BST vulnerability and test the repos
```

## Note

In this repo are contained some legacy scripts that are not used anymore.
They are kept for reference and can be found in the `legacy` folder.
