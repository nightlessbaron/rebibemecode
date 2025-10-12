#!/usr/bin/env python3
"""
Main script with argument parsing for R_base, R_old URLs and work directory.
"""

import argparse
import os
import subprocess
from datetime import datetime
import requests
from termcolor import cprint

def verify_if_url_is_open_github(github_url):
    """
    Check if a GitHub repository URL has valid format and is accessible.
    Uses a simple approach that doesn't hit GitHub API rate limits.

    Args:
        github_url (str): e.g. "https://github.com/user/repo"

    Returns:
        bool: True if URL format is valid and accessible, False otherwise
    """
    # Basic URL format validation
    if not github_url.startswith("https://github.com/"):
        print(f"Not a valid GitHub URL: {github_url}")
        return False

    # Extract "user/repo" parts
    parts = github_url.rstrip("/").split("/")
    if len(parts) < 5:
        print(f"Invalid GitHub repository URL format: {github_url}")
        return False

    user, repo = parts[-2], parts[-1]
    
    # Basic validation - check if user and repo names are reasonable
    if not user or not repo or len(user) == 0 or len(repo) == 0:
        print(f"Invalid user or repository name in URL: {github_url}")
        return False
    
    # Try a simple HEAD request to the repository page (not API)
    try:
        response = requests.head(github_url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            return True
        else:
            print(f"Repository not accessible: {github_url} (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Network error checking repository: {github_url} - {str(e)}")
        # For network errors, we'll assume the URL format is valid and continue
        # This prevents network issues from blocking the entire process
        return True


def robust_git_clone(repo_url, target_dir, timeout=30):
    """
    Clone a git repository with timeout and error handling.
    Tries 'main' branch first, then falls back to 'master' if main doesn't exist.
    
    Args:
        repo_url (str): The repository URL to clone
        target_dir (str): The target directory for cloning
        timeout (int): Timeout in seconds (default: 30)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Cloning {repo_url} to {target_dir} (timeout: {timeout}s)...")
        
        # Try cloning 'main' branch first
        print("Attempting to clone 'main' branch...")
        result = subprocess.run(
            ["git", "clone", "--branch", "main", "--depth", "1", repo_url, target_dir],
            timeout=timeout,
            text=True,
            check=False  # Don't raise exception on non-zero exit code
        )
        
        if result.returncode == 0:
            print(f"✓ Successfully cloned {repo_url} (main branch)")
            return True
        else:
            print(f"Failed to clone 'main' branch (exit code: {result.returncode})")
            print("Attempting to clone 'master' branch...")
            
            # Try cloning 'master' branch as fallback
            result = subprocess.run(
                ["git", "clone", "--branch", "master", "--depth", "1", repo_url, target_dir],
                timeout=timeout,
                text=True,
                check=False  # Don't raise exception on non-zero exit code
            )
            
            if result.returncode == 0:
                print(f"✓ Successfully cloned {repo_url} (master branch)")
                return True
            else:
                print(f"✗ Failed to clone {repo_url} with both 'main' and 'master' branches (exit code: {result.returncode})")
                return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ Clone operation timed out after {timeout} seconds: {repo_url}")
        return False
    except FileNotFoundError:
        print("✗ Git command not found. Please ensure git is installed.")
        return False
    except Exception as e:
        print(f"✗ Unexpected error cloning {repo_url}: {str(e)}")
        return False


def revive_code(r_base, r_old, workdir):
    """Revive code from the old repository to the new repository."""
    cprint("--------------------------------", "green")
    cprint("Revive code with the following parameters:", "green")
    cprint(f"R_base: {r_base}", "green")
    cprint(f"R_old: {r_old}", "green")
    cprint(f"Work directory: {workdir}", "green")
    cprint("--------------------------------", "green")
    
    # Verification
    if not verify_if_url_is_open_github(r_base):
        raise ValueError(f"R_base is not a valid GitHub repository: {r_base}")
    if not verify_if_url_is_open_github(r_old):
        raise ValueError(f"R_old is not a valid GitHub repository: {r_old}")

    # Clone github repository to correct folders with robust handling
    success_base = robust_git_clone(r_base, f"{workdir}/r_base", timeout=120)
    success_old = robust_git_clone(r_old, f"{workdir}/r_old", timeout=120)
    
    if not success_base:
        raise RuntimeError(f"Failed to clone base repository: {r_base}")
    if not success_old:
        raise RuntimeError(f"Failed to clone old repository: {r_old}")
    
    print("✓ All repositories cloned successfully!")

if __name__ == "__main__":
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Main script with URL arguments and work directory setup"
    )
    
    parser.add_argument(
        "--R_base",
        type=str,
        default="https://github.com/Farama-Foundation/Gymnasium",
        help="Base repository URL (default: %(default)s)"
    )
    
    parser.add_argument(
        "--R_old", 
        type=str,
        default="https://github.com/igilitschenski/multi_car_racing/",
        help="Old repository URL (default: %(default)s)"
    )
    
    parser.add_argument(
        "--workdir",
        type=str,
        default="./work_dir",
        help=f"Working directory (default: ./work_dir)"
    )
    
    args = parser.parse_args()

    # Add time to the work directory
    args.workdir = f"{args.workdir}/invocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create the work directory if it doesn't exist
    os.makedirs(args.workdir, exist_ok=True)
    print(f"Created work directory: {args.workdir}")
    
    # Revive code
    revive_code(args.R_base, args.R_old, args.workdir)

