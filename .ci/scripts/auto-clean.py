#!/usr/bin/env python3

import pathlib, shutil
import subprocess

import time

import argparse
import logging

# Get the last modification time of a file using git
def get_last_modification_time(file: pathlib.Path, git_base_dir: pathlib.Path) -> float:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                git_base_dir.resolve().as_posix(),
                "log",
                "-1",
                "--format=%ct",
                "--",
                file.resolve().as_posix()
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        # the result will be a unix timestamp
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get last modification time for {file}: {e}")
        return None

# Delete file if it is older than a certain number of days
# Returns True if file was deleted, False otherwise
def remove_if_too_old(file: pathlib.Path, days: int, git_base_dir: pathlib.Path) -> bool:
    if not file.exists():
        logging.error(f"File {file} does not exist")
        return False
    reference_time = time.time() - days * 24 * 60 * 60
    last_modified = get_last_modification_time(file, git_base_dir)
    logging.debug(f"File {file} was last modified at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_modified))}")
    if last_modified >= reference_time:
        return False    
    logging.info(f"Deleting {file}")
    if file.is_dir():
        shutil.rmtree(file)
    else:
        file.unlink()
    return True

# Check if a file is a global artifact
# This function assumes that any directory that is not
# named with 11 digits is a global artifact
# This is a heuristic that works for the current CI setup,
# because the other directories are named with the run ID
def is_global_artifact(file: pathlib.Path) -> bool:
    if len(file.stem) != 11:
        return True
    if not file.stem.isdigit():
        return True
    return False
    

# Clean up CI artifacts in a directory
# Requires specific directory structure:
# - <directory>
#   - <org1>
#     - <repo1>
#       - <run1>
#         - <artifact1>
#         - <artifact2>
#       - <run2>
#         - <artifact1>
#         - <artifact2>
#     - <repo2>
#       - <run3>
#         - <artifact1>
#         - <artifact2>
#   - <org2>
#     - <repo3>
#       - <run4>
#         - <artifact1>
#         - <artifact2>
def clean_up_ci_artifacts(
    directory: pathlib.Path,
    days: int,
    clean_up_global_artifacts: bool,
    git_base_dir: pathlib.Path
):
    logging.info(f"Cleaning up CI artifacts in {directory}")
    for org_dir in directory.iterdir():
        for repo_dir in org_dir.iterdir():
            for run_dir in repo_dir.iterdir():
                is_global = is_global_artifact(run_dir)
                if is_global and not clean_up_global_artifacts:
                    continue 
                remove_if_too_old(run_dir, days, git_base_dir)
            if not list(repo_dir.iterdir()):
                logging.info(f"Deleting empty directory {repo_dir}")
                repo_dir.rmdir()
        if not list(org_dir.iterdir()):
            logging.info(f"Deleting empty directory {org_dir}")
            org_dir.rmdir()

def main():
    parser = argparse.ArgumentParser(description="Clean up CI artifacts")
    parser.add_argument("--ci-artifacts-dir", type=pathlib.Path, help="Directory containing CI artifacts")
    parser.add_argument("--days", type=int, default=7, help="Delete files older than this number of days")
    parser.add_argument("--clean-up-global-artifacts", type=bool, default=False, help="Delete global artifacts")
    parser.add_argument("--git-base-dir", type=pathlib.Path, help="Base directory for git commands")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    clean_up_ci_artifacts(
        args.ci_artifacts_dir,
        args.days,
        args.clean_up_global_artifacts,
        args.git_base_dir
    )

if __name__ == "__main__":
    main()
