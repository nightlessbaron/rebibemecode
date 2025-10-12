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
from classes.utils import clone_repos
from classes.cursor_cli_agent import CursorCLIAgent
import classes.utils as utils

GLOBAL_CONTEXT = """
Global context:
You are an integration agent, whose job is to make older repositories compatible latest ones. You will be given 2 repositories, R_base and R_old, and you need to integrate the R_old code into R_base. These are the high-level objectives you should operate on
You are not allowed to make a lot of changes to the code and environment in R_base. Only make absolutely necessary changes without which R_old can never be integrated with R_base (for example, if E_base doesn't have scipy, and R_old uses it, you are allowed to install scipy in R_base)
You are allowed to modify code in R_old to make it compatible with R_base, as long as it doesn't change any core features/functionality of R_old.
I will provide you with specifics in the next prompt

Specific work to do:
"""

def revive_code(git_repo_base, git_repo_old, workdir):
    global GLOBAL_CONTEXT
    """Revive code from the old repository to the new repository."""
    cprint("--------------------------------", "green")
    cprint("Revive code with the following parameters:", "green")
    cprint(f"git_repo_base: {git_repo_base}", "green")
    cprint(f"R_old: {git_repo_old}", "green")
    cprint(f"Work directory: {workdir}", "green")
    cprint("--------------------------------", "green")

    # clone_repos(git_repo_base, r_old, workdir)
    GLOBAL_CONTEXT = GLOBAL_CONTEXT + f"R_base: {git_repo_base}\nR_old: {git_repo_old}"

    # Initialize the agent
    agent = CursorCLIAgent()

    # Setup the r_base environment
    is_env_setup_correctly = utils.setup_r_base_environment(agent, workdir, GLOBAL_CONTEXT)
    if not is_env_setup_correctly:
        cprint("R_base environment setup failed", "red")
        return
    cprint("R_base environment setup complete", "green")
    
    # Setup the r_old environment
    is_env_setup_correctly = utils.setup_r_old_environment(agent, git_repo_old, workdir, GLOBAL_CONTEXT)
    if not is_env_setup_correctly:
        cprint("R_old environment setup failed", "red")
        return
    cprint("R_old environment setup complete", "green")
    
    # Resolve dependencies
    is_dependencies_resolved = utils.resolve_dependencies(agent, git_repo_base, git_repo_old, workdir, GLOBAL_CONTEXT)
    if not is_dependencies_resolved:
        cprint("Dependencies resolution failed", "red")
        return
    cprint("Dependencies resolution complete", "green")

    # Final verification
    base_setup_correct, old_setup_correct = utils.verify_complete_integration(agent, git_repo_base, git_repo_old, workdir, GLOBAL_CONTEXT)
    if not base_setup_correct:
        cprint("Base setup verification failed", "red")
        return
    cprint("Base setup verification complete", "green")
    if not old_setup_correct:
        cprint("Old setup verification failed", "red")
        return
    cprint("Old setup verification complete", "green")
    cprint("All setup verification complete", "green")
    

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
    # args.workdir = f"{args.workdir}/invocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    args.workdir = f"{args.workdir}/invocation_20251011_204741"
    
    # Create the work directory if it doesn't exist
    os.makedirs(args.workdir, exist_ok=True)
    print(f"Created work directory: {args.workdir}")
    
    # Revive code
    revive_code(args.R_base, args.R_old, args.workdir)

