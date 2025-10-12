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
import weave
from dotenv import load_dotenv
from classes.utils import clone_repos
from classes.revive_agent import ReviveAgent
import classes.utils as utils

# Load environment variables
load_dotenv()

GLOBAL_CONTEXT = """
Global context:
You are an integration agent, whose job is to make older repositories compatible latest ones. You will be given 2 repositories, R_base and R_old, and you need to integrate the R_old code into R_base. These are the high-level objectives you should operate on
You are not allowed to make a lot of changes to the code and environment in R_base. Only make absolutely necessary changes without which R_old can never be integrated with R_base (for example, if E_base doesn't have scipy, and R_old uses it, you are allowed to install scipy in R_base)
You are allowed to modify code in R_old to make it compatible with R_base, as long as it doesn't change any core features/functionality of R_old.
The repository might have a mistake log at ./mistake_log.md. If it exists, read it and keep it in mind.
Github repos R_base and R_old will be cloned for you, don't clone them again (if you dont find them you made a path error).
Make sure to resolve all dependency issues, especially related to version mismatches (by upgrading package and code accordingly)

IMPORTANT - Daytona MCP Tools Available:
You have access to Daytona MCP tools for running commands on remote sandboxes. If you need to:
- Create a remote development environment
- Run commands in an isolated sandbox
- Test code in a clean environment
You can use the Daytona MCP tools that are available in your tool set.

I will provide you with specifics in the prompt below.

Specific work to do:
"""


@weave.op()
def revive_code(git_repo_base, git_repo_old, workdir, model):
    global GLOBAL_CONTEXT
    GLOBAL_CONTEXT = GLOBAL_CONTEXT + f"R_base: {git_repo_base}\nR_old: {git_repo_old}\n"
    """Revive code from the old repository to the new repository."""

    cprint("--------------------------------", "green")
    cprint("Revive code with the following parameters:", "green")
    cprint(f"Model: {model}", "green")
    cprint(f"git_repo_base: {git_repo_base}", "green")
    cprint(f"R_old: {git_repo_old}", "green")
    cprint(f"Work directory: {workdir}", "green")
    cprint("--------------------------------", "green")

    # Clone the repositories
    with weave.attributes(
        {"step": "clone_repositories", "r_base": git_repo_base, "r_old": git_repo_old}
    ):
        clone_repos(git_repo_base, git_repo_old, workdir)

    # Initialize the agent
    agent = ReviveAgent(model)

    # Setup the r_base environment
    with weave.attributes({"step": "setup_r_base_environment", "workdir": workdir}):
        is_env_setup_correctly = utils.setup_r_base_environment(
            agent, workdir, GLOBAL_CONTEXT
        )
        if not is_env_setup_correctly:
            cprint("R_base environment setup failed", "red")
            return {"success": False, "step": "setup_r_base_environment"}
        cprint("R_base environment setup complete", "green")

    # Setup the r_old environment
    with weave.attributes({"step": "setup_r_old_environment", "workdir": workdir}):
        is_env_setup_correctly = utils.setup_r_old_environment(
            agent, git_repo_old, workdir, GLOBAL_CONTEXT
        )
        if not is_env_setup_correctly:
            cprint("R_old environment setup failed", "red")
            return {"success": False, "step": "setup_r_old_environment"}
        cprint("R_old environment setup complete", "green")

    # Resolve dependencies
    with weave.attributes({"step": "resolve_dependencies", "workdir": workdir}):
        is_dependencies_resolved = utils.resolve_dependencies(
            agent, git_repo_base, git_repo_old, workdir, GLOBAL_CONTEXT
        )
        if not is_dependencies_resolved:
            cprint("Dependencies resolution failed", "red")
            return {"success": False, "step": "resolve_dependencies"}
        cprint("Dependencies resolution complete", "green")

    # Final verification
    with weave.attributes({"step": "final_verification", "workdir": workdir}):
        base_setup_correct, old_setup_correct = utils.verify_complete_integration(
            agent, git_repo_base, git_repo_old, workdir, GLOBAL_CONTEXT
        )
        cprint("Final verification status:", "green")
        base_color = "green" if base_setup_correct else "red"
        old_color = "green" if old_setup_correct else "red"
        cprint(f"Base setup verification: {base_color=='green'}", base_color)
        cprint(f"Old setup verification: {old_color=='green'}", old_color)

    return {
        "success": base_setup_correct and old_setup_correct,
        "base_setup_correct": base_setup_correct,
        "old_setup_correct": old_setup_correct,
        "workdir": workdir,
    }


if __name__ == "__main__":
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Main script with URL arguments and work directory setup"
    )

    parser.add_argument(
        "--R_base",
        type=str,
        default="https://github.com/Farama-Foundation/Gymnasium",
        help="Base repository URL (default: %(default)s)",
    )

    parser.add_argument(
        "--R_old",
        type=str,
        default="https://github.com/igilitschenski/multi_car_racing/",
        help="Old repository URL (default: %(default)s)",
    )

    parser.add_argument(
        "--workdir",
        type=str,
        default="./work_dir",
        help=f"Working directory (default: ./work_dir)",
    )

    parser.add_argument(
        "--weave-project",
        type=str,
        default="rebibemecode-integration",
        help="Weave project name for tracking (default: rebibemecode-integration)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="auto",
        help="Model to use for the CLI agent (default: auto)"
    )

    args = parser.parse_args()

    # Initialize Weave tracking
    weave.init(args.weave_project)
    print(f"🔍 Weave tracking initialized for project: {args.weave_project}")

    # Add time to the work directory
    args.workdir = (
        f"{args.workdir}/invocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    # Create the work directory if it doesn't exist
    os.makedirs(args.workdir, exist_ok=True)
    print(f"Created work directory: {args.workdir}")

    # Revive code with Weave tracking
    with weave.attributes(
        {
            "invocation_time": datetime.now().isoformat(),
            "r_base_url": args.R_base,
            "r_old_url": args.R_old,
            "work_directory": args.workdir,
        }
    ):
        result = revive_code(args.R_base, args.R_old, args.workdir, args.model)
        print(f"\n✅ Final result: {result}")
