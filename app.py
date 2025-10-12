#!/usr/bin/env python3
"""
Flask web application for the code revive backend.
"""

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    Response,
    stream_with_context,
)
import os
import threading
import uuid
import queue
from datetime import datetime
from termcolor import cprint
import weave
from classes.revive_agent import ReviveAgent
import classes.utils as utils

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Initialize Weave for Flask app
weave.init("rebibemecode-web-app")

# Store job statuses in memory (for production, use Redis or database)
job_status = {}

# Store streaming queues for each job
streaming_queues = {}

GLOBAL_CONTEXT = """
Global context:
You are an integration agent, whose job is to make older repositories compatible latest ones. You will be given 2 repositories, R_base and R_old, and you need to integrate the R_old code into R_base. These are the high-level objectives you should operate on
You are not allowed to make a lot of changes to the code and environment in R_base. Only make absolutely necessary changes without which R_old can never be integrated with R_base (for example, if E_base doesn't have scipy, and R_old uses it, you are allowed to install scipy in R_base)
You are allowed to modify code in R_old to make it compatible with R_base, as long as it doesn't change any core features/functionality of R_old.
I will provide you with specifics in the next prompt

Specific work to do:
"""


@weave.op()
def revive_code_task(job_id, git_repo_base, git_repo_old, workdir):
    """Background task to run the code revival process."""
    try:
        # Track job metadata in Weave
        with weave.attributes(
            {
                "job_id": job_id,
                "r_base_url": git_repo_base,
                "r_old_url": git_repo_old,
                "work_directory": workdir,
                "started_at": datetime.now().isoformat(),
            }
        ):
            job_status[job_id]["status"] = "running"
            job_status[job_id]["current_step"] = "Initializing agent"

            # Create a queue for streaming output
            streaming_queues[job_id] = queue.Queue()

            def stream_callback(text):
                """Callback to push text to the streaming queue."""
                try:
                    streaming_queues[job_id].put(text)
                except:
                    pass  # Queue might be full or closed

            global_context = (
                GLOBAL_CONTEXT + f"R_base: {git_repo_base}\nR_old: {git_repo_old}"
            )

            # Initialize the agent
            agent = ReviveAgent()

            # Setup the r_base environment
            job_status[job_id]["current_step"] = "Setting up R_base environment"
            streaming_queues[job_id].put("\n\n=== Setting up R_base environment ===\n")
            with weave.attributes({"step": "setup_r_base", "job_id": job_id}):
                is_env_setup_correctly = utils.setup_r_base_environment(
                    agent, workdir, global_context, stream_callback
                )
                if not is_env_setup_correctly:
                    job_status[job_id]["status"] = "failed"
                    job_status[job_id]["error"] = "R_base environment setup failed"
                    streaming_queues[job_id].put(None)  # Signal end
                    return {"success": False, "step": "setup_r_base"}

            # Setup the r_old environment
            job_status[job_id]["current_step"] = "Setting up R_old environment"
            streaming_queues[job_id].put("\n\n=== Setting up R_old environment ===\n")
            with weave.attributes({"step": "setup_r_old", "job_id": job_id}):
                is_env_setup_correctly = utils.setup_r_old_environment(
                    agent, git_repo_old, workdir, global_context, stream_callback
                )
                if not is_env_setup_correctly:
                    job_status[job_id]["status"] = "failed"
                    job_status[job_id]["error"] = "R_old environment setup failed"
                    streaming_queues[job_id].put(None)  # Signal end
                    return {"success": False, "step": "setup_r_old"}

            # Resolve dependencies
            job_status[job_id]["current_step"] = "Resolving dependencies"
            streaming_queues[job_id].put("\n\n=== Resolving dependencies ===\n")
            with weave.attributes({"step": "resolve_dependencies", "job_id": job_id}):
                is_dependencies_resolved = utils.resolve_dependencies(
                    agent,
                    git_repo_base,
                    git_repo_old,
                    workdir,
                    global_context,
                    stream_callback,
                )
                if not is_dependencies_resolved:
                    job_status[job_id]["status"] = "failed"
                    job_status[job_id]["error"] = "Dependencies resolution failed"
                    streaming_queues[job_id].put(None)  # Signal end
                    return {"success": False, "step": "resolve_dependencies"}

            # Final verification
            job_status[job_id]["current_step"] = "Final verification"
            streaming_queues[job_id].put("\n\n=== Final verification ===\n")
            with weave.attributes({"step": "final_verification", "job_id": job_id}):
                base_setup_correct, old_setup_correct = (
                    utils.verify_complete_integration(
                        agent,
                        git_repo_base,
                        git_repo_old,
                        workdir,
                        global_context,
                        stream_callback,
                    )
                )

                if not base_setup_correct or not old_setup_correct:
                    job_status[job_id]["status"] = "failed"
                    job_status[job_id][
                        "error"
                    ] = f"Verification failed - Base: {base_setup_correct}, Old: {old_setup_correct}"
                    streaming_queues[job_id].put(None)  # Signal end
                    return {
                        "success": False,
                        "step": "final_verification",
                        "base_correct": base_setup_correct,
                        "old_correct": old_setup_correct,
                    }

            job_status[job_id]["status"] = "completed"
            job_status[job_id]["current_step"] = "All tasks completed successfully"
            job_status[job_id]["work_directory"] = workdir

            # Get and display total stats
            total_stats = agent.get_total_stats()
            job_status[job_id]["total_tool_calls"] = total_stats["tool_calls"]
            job_status[job_id]["total_tokens"] = total_stats["tokens"]

            final_stats_msg = f"\n\n{'='*80}\n📊 FINAL STATS FOR THIS JOB\n{'='*80}\nTotal Tool Calls: {total_stats['tool_calls']}\nTotal Tokens: ~{total_stats['tokens']}\n{'='*80}\n"
            streaming_queues[job_id].put(final_stats_msg)

            streaming_queues[job_id].put(None)  # Signal end

            return {
                "success": True,
                "job_id": job_id,
                "workdir": workdir,
                "base_correct": base_setup_correct,
                "old_correct": old_setup_correct,
            }

    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)

        # Get stats even on failure
        if "agent" in locals():
            total_stats = agent.get_total_stats()
            job_status[job_id]["total_tool_calls"] = total_stats["tool_calls"]
            job_status[job_id]["total_tokens"] = total_stats["tokens"]

            if job_id in streaming_queues:
                final_stats_msg = f"\n\n{'='*80}\n📊 STATS BEFORE FAILURE\n{'='*80}\nTotal Tool Calls: {total_stats['tool_calls']}\nTotal Tokens: ~{total_stats['tokens']}\n{'='*80}\n"
                streaming_queues[job_id].put(final_stats_msg)

        if job_id in streaming_queues:
            streaming_queues[job_id].put(None)  # Signal end
        return {"success": False, "error": str(e)}


@app.route("/")
def index():
    """Render the main page with the form."""
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit_job():
    """Handle form submission and start the background task."""
    data = request.json
    r_base = data.get("r_base", "").strip()
    r_old = data.get("r_old", "").strip()

    # Validate inputs
    if not r_base or not r_old:
        return jsonify({"error": "Both repository URLs are required"}), 400

    # Create job ID and work directory
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workdir = f"./work_dir/invocation_{timestamp}_{job_id[:8]}"
    os.makedirs(workdir, exist_ok=True)

    # Initialize job status
    job_status[job_id] = {
        "status": "queued",
        "current_step": "Queued",
        "r_base": r_base,
        "r_old": r_old,
        "work_directory": workdir,
        "started_at": datetime.now().isoformat(),
    }

    # Start background thread
    thread = threading.Thread(
        target=revive_code_task, args=(job_id, r_base, r_old, workdir)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id, "message": "Job submitted successfully"})


@app.route("/status/<job_id>")
def get_status(job_id):
    """Get the status of a job."""
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job_status[job_id])


@app.route("/results/<job_id>")
def results(job_id):
    """Render the results page for a job."""
    if job_id not in job_status:
        return "Job not found", 404

    return render_template("results.html", job_id=job_id, job_data=job_status[job_id])


@app.route("/stream/<job_id>")
def stream(job_id):
    """Server-Sent Events endpoint for streaming agent output."""
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        """Generator function for SSE."""
        # Wait for the queue to be created
        max_wait = 30
        wait_count = 0
        while job_id not in streaming_queues and wait_count < max_wait:
            import time

            time.sleep(0.1)
            wait_count += 1

        if job_id not in streaming_queues:
            yield f"data: ERROR: Streaming not available\n\n"
            return

        q = streaming_queues[job_id]

        while True:
            try:
                # Get text from queue with timeout
                text = q.get(timeout=1.0)

                # None signals the end of the stream
                if text is None:
                    yield f"data: [DONE]\n\n"
                    break

                # Send the text chunk as SSE
                # Escape newlines for SSE format
                text_escaped = text.replace("\n", "\\n")
                yield f"data: {text_escaped}\n\n"

            except queue.Empty:
                # Send a heartbeat to keep connection alive
                yield f": heartbeat\n\n"

                # Check if job has failed or completed
                if job_id in job_status:
                    status = job_status[job_id]["status"]
                    if status in ["completed", "failed"]:
                        yield f"data: [DONE]\n\n"
                        break

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000, threaded=True)
