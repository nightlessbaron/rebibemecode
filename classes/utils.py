import subprocess
import requests
from termcolor import cprint
import os
import weave


@weave.op()
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
            print(
                f"Repository not accessible: {github_url} (Status: {response.status_code})"
            )
            return False
    except requests.exceptions.RequestException as e:
        print(f"Network error checking repository: {github_url} - {str(e)}")
        # For network errors, we'll assume the URL format is valid and continue
        # This prevents network issues from blocking the entire process
        return True


@weave.op()
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
            check=False,  # Don't raise exception on non-zero exit code
        )

        if result.returncode == 0:
            print(f"✓ Successfully cloned {repo_url} (main branch)")
            return True
        else:
            print(f"Failed to clone 'main' branch (exit code: {result.returncode})")
            print("Attempting to clone 'master' branch...")

            # Try cloning 'master' branch as fallback
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--branch",
                    "master",
                    "--depth",
                    "1",
                    repo_url,
                    target_dir,
                ],
                timeout=timeout,
                text=True,
                check=False,  # Don't raise exception on non-zero exit code
            )

            if result.returncode == 0:
                print(f"✓ Successfully cloned {repo_url} (master branch)")
                return True
            else:
                print(
                    f"✗ Failed to clone {repo_url} with both 'main' and 'master' branches (exit code: {result.returncode})"
                )
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


@weave.op()
def clone_repos(r_base, r_old, workdir):
    # Verification
    if not verify_if_url_is_open_github(r_base):
        raise ValueError(f"R_base is not a valid GitHub repository: {r_base}")
    if not verify_if_url_is_open_github(r_old):
        raise ValueError(f"R_old is not a valid GitHub repository: {r_old}")

    # Clone github repository to correct folders with robust handling
    with weave.attributes(
        {"r_base_url": r_base, "r_old_url": r_old, "workdir": workdir}
    ):
        success_base = robust_git_clone(r_base, f"{workdir}/r_base", timeout=120)
        success_old = robust_git_clone(r_old, f"{workdir}/r_old", timeout=120)

        if not success_base:
            raise RuntimeError(f"Failed to clone base repository: {r_base}")
        if not success_old:
            raise RuntimeError(f"Failed to clone old repository: {r_old}")

        cprint("All repositories cloned successfully", "green")
        return {"success": True, "base_cloned": success_base, "old_cloned": success_old}


@weave.op()
def summarize_base_repo_setup(agent, workdir, GLOBAL_CONTEXT, stream_callback=None):
    command = f"""
    1. Read the repository at {workdir}/r_base at a high level.
    2. Write a file summarize_r_base.md in the folder {workdir} that summarizes what the repository is about.
    3. Make a script {workdir}/setup_r_base.sh to make a conda environment env_r_base and install the dependencies to run r_base
    4. Run the {workdir}/setup_r_base.sh and make sure the conda environment is setup correctly. Delete the env env_r_base if it already exists.
    5. Write a single file {workdir}/test_base.sh which tests if r_base is working properly.
    """
    result = agent.run_prompt(GLOBAL_CONTEXT + command, stream_callback=stream_callback)
    return result


@weave.op()
def verify_base_repo_setup(agent, workdir, GLOBAL_CONTEXT):
    to_verify_files = [
        f"{workdir}/summarize_r_base.md",
        f"{workdir}/setup_r_base.sh",
        f"{workdir}/test_base.sh",
    ]
    for file in to_verify_files:
        if not os.path.exists(file):
            return False
    return True


@weave.op()
def verify_if_env_is_setup_correctly(
    agent, workdir, GLOBAL_CONTEXT, stream_callback=None
):
    command = f"""
    1. Activate env_r_base and make the script {workdir}/test_base.sh run correctly. If yes, append
             'r_base: env setup and unit tests successful'
       else write
             'r_base: env setup and unit tests failed'
       in {workdir}/agent_summary.txt
    """
    result = agent.run_prompt(GLOBAL_CONTEXT + command, stream_callback=stream_callback)

    # Read the file {workdir}/agent_summary.txt
    with open(f"{workdir}/agent_summary.txt", "r") as f:
        return "r_base: env setup and unit tests successful" in f.read()


@weave.op()
def setup_r_base_environment(agent, workdir, GLOBAL_CONTEXT, stream_callback=None):
    # Make the conda environment and generate summary
    cprint("Making the conda environment and setting up unit tests for r_base", "green")
    summarize_base_repo_setup(agent, workdir, GLOBAL_CONTEXT, stream_callback)
    summary_and_setup_complete = verify_base_repo_setup(agent, workdir, GLOBAL_CONTEXT)
    if not summary_and_setup_complete:
        cprint("Summary and setup for r_base failed", "red")
        return False
    cprint("Summary and setup for r_base complete", "green")

    # Verify the conda environment and unit tests
    cprint("Verifying the conda environment and unit tests", "green")
    is_env_setup_correctly = verify_if_env_is_setup_correctly(
        agent, workdir, GLOBAL_CONTEXT, stream_callback
    )
    if not is_env_setup_correctly:
        cprint("Conda environment and unit tests verification failed", "red")
        return False
    cprint("Conda environment and unit tests verified", "green")
    return is_env_setup_correctly


@weave.op()
def setup_r_old_environment(
    agent, r_old, workdir, GLOBAL_CONTEXT, stream_callback=None
):
    """
    We will clone the repo and read code and summarize it.
    We will
    """
    prompt = f"""
    1. Clone the repo from {r_old}, and make sure you have the code at {workdir}/r_old
    2. Read code and dependencies from {workdir}/r_old and understand at a high level what it is
       Summarize it in {workdir}/summarize_r_old.md
    3. Write a single file {workdir}/test_old.sh which tests if r_old is working properly.
    """
    result = agent.run_prompt(GLOBAL_CONTEXT + prompt, stream_callback=stream_callback)

    # Assert if the the files have been created
    if not os.path.exists(f"{workdir}/summarize_r_old.md"):
        raise RuntimeError(f"Summarize_r_old.md not created")
    if not os.path.exists(f"{workdir}/test_old.sh"):
        raise RuntimeError(f"Test_old.sh not created")

    return True


@weave.op()
def resolve_dependencies(
    agent, r_base, r_old, workdir, GLOBAL_CONTEXT, stream_callback=None
):
    prompt = f"""
    1. Make obvious changes to the {workdir}/r_old code so that it can run with the env_r_base environment
    2. Activate env_r_base and try to run {workdir}/test_old.sh. If we get errors, iterate and try to fix the code in R_old.
       Do not pip install everything from R_old, only add dependencies / make modifications in env_r_base if absolutely necessary.
    3. If you modify env_r_base, make sure you run {workdir}/test_base.sh to verify test_base.sh doesn't break
    4. Verify we can run {workdir}/test_old.sh with env_r_base. If yes, append
             'r_old: env setup and unit tests successful'
       else write
             'r_old: env setup and unit tests failed'
       in {workdir}/agent_summary.txt
    5. Make sure that the base environment is still working correctly by running {workdir}/test_base.sh.
       If not can you please iterate and fix it
    """
    result = agent.run_prompt(GLOBAL_CONTEXT + prompt, stream_callback=stream_callback)

    # Read the file {workdir}/agent_summary.txt
    with open(f"{workdir}/agent_summary.txt", "r") as f:
        return "r_old: env setup and unit tests successful" in f.read()


@weave.op()
def verify_complete_integration(
    agent, r_base, r_old, workdir, GLOBAL_CONTEXT, stream_callback=None
):
    prompt = f"""
    1. Activate env_r_base
    2. Run and verify test_old.sh works correctly, if yes append
             'r_old: env setup and unit tests successful'
       else write
             'r_old: env setup and unit tests failed'
       in {workdir}/final_summary.txt
    3. Run and verify test_base.sh works correctly, if yes append
             'r_base: env setup and unit tests successful'
       else write
             'r_base: env setup and unit tests failed'
       in {workdir}/final_summary.txt
    """
    result = agent.run_prompt(GLOBAL_CONTEXT + prompt, stream_callback=stream_callback)

    # Get 2 variables base_setup_correct and old_setup_correct
    with open(f"{workdir}/final_summary.txt", "r") as f:
        content = f.read()
        old_setup_correct = "r_old: env setup and unit tests successful" in content
        base_setup_correct = "r_base: env setup and unit tests successful" in content
    return base_setup_correct, old_setup_correct
