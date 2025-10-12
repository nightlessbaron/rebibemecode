#!/usr/bin/env python3
"""
Flask web application for the code revive backend.
"""

# Print ASCII logo in green
print("\033[92m")  # Green color
print("██████  ███████ ██    ██ ██ ██    ██ ███████ ██████  ")
print("██   ██ ██      ██    ██ ██ ██    ██ ██      ██   ██ ")
print("██████  █████   ██    ██ ██ ██    ██ █████   ██████  ")
print("██   ██ ██       ██  ██  ██  ██  ██  ██      ██   ██ ")
print("██   ██ ███████   ████   ██   ████   ███████ ██   ██ ")
print("\033[0m")  # Reset color
print()

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
import subprocess

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

IMPORTANT COMMAND EXECUTION RULES:
- When running shell commands, ALWAYS use proper syntax and avoid output redirection issues
- DO NOT create files with names starting with '=' (like =1.2.0, =0.9, etc.)
- When installing packages with specific versions, use quotes: pip install "package==1.2.0" NOT pip install package==1.2.0
- When running conda or pip commands, be explicit about the environment activation first
- Avoid using shell redirection operators (>, >>, <, |) unless absolutely necessary and you know the correct file path
- If a command creates unexpected files (like =something), stop and use a different approach
- Always verify commands before running them, especially those with version specifiers or special characters

I will provide you with specifics in the next prompt

Specific work to do:
"""


@weave.op()
def revive_code_task(job_id, git_repo_base, git_repo_old, workdir):
    """Background task to run the code revival process."""
    try:
        # Don't set the URL here - let the wrapper handle it
        # job_status[job_id]["weave_trace_url"] = "https://wandb.ai/mbzuai-llm/rebibemecode-web-app/weave"
        
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
            agent = ReviveAgent(model="sonnet-4.5")

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


def run_revive_task_with_weave_tracking(job_id, git_repo_base, git_repo_old, workdir):
    """Wrapper to run the task and capture the Weave call ID."""
    try:
        print(f"🚀 Starting Weave-tracked task for job {job_id[:8]}")
        
        # Use .call() to get the call object
        result, call = revive_code_task.call(job_id, git_repo_base, git_repo_old, workdir)
        
        print(f"✅ Task completed. Call object type: {type(call)}")
        print(f"✅ Call ID: {call.id if call else 'None'}")
        
        # Update the job status with the Weave trace URL
        if call and hasattr(call, 'id') and call.id:
            weave_url = f"https://wandb.ai/mbzuai-llm/rebibemecode-web-app/weave/calls/{call.id}"
            job_status[job_id]["weave_trace_url"] = weave_url
            print(f"🔍 Weave trace URL for job {job_id[:8]}: {weave_url}")
        else:
            print(f"⚠️ No call object or call ID available for job {job_id[:8]}")
        
        return result
    except Exception as e:
        print(f"❌ Error in Weave tracking wrapper: {e}")
        import traceback
        traceback.print_exc()
        # Still run the task even if tracking fails
        return revive_code_task(job_id, git_repo_base, git_repo_old, workdir)


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

    # Start background thread with Weave tracking wrapper
    thread = threading.Thread(
        target=run_revive_task_with_weave_tracking, args=(job_id, r_base, r_old, workdir)
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


@app.route("/weave-data/<job_id>")
def get_weave_data(job_id):
    """Fetch Weave trace data for a specific job."""
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404
    
    weave_trace_url = job_status[job_id].get("weave_trace_url")
    if not weave_trace_url:
        return jsonify({"error": "Weave trace not available yet"}), 404
    
    try:
        # Extract call ID from the URL
        if "/calls/" in weave_trace_url:
            call_id = weave_trace_url.split("/calls/")[-1].split("?")[0]
        else:
            # URL doesn't contain call ID yet
            print(f"⚠️ Weave URL doesn't contain call ID: {weave_trace_url}")
            return jsonify({"error": "Weave call ID not available yet"}), 404
        
        print(f"🔍 Fetching Weave data for call_id: {call_id}")
        
        # Initialize Weave client (reuse existing client if already initialized)
        try:
            client = weave.init("rebibemecode-web-app")
        except Exception as e:
            print(f"⚠️ Weave already initialized: {e}")
            # Get existing client
            import weave.trace.weave_client as weave_client_module
            client = weave_client_module.get_weave_client()
        
        if not client:
            return jsonify({"error": "Failed to initialize Weave client"}), 500
        
        # Get the call object
        try:
            call = client.get_call(call_id)
        except Exception as e:
            print(f"❌ Error getting call: {e}")
            return jsonify({"error": f"Failed to get call: {str(e)}"}), 500
        
        if not call:
            return jsonify({"error": "Call not found"}), 404
        
        print(f"✅ Found call: {call.op_name}")
        
        # Build a comprehensive trace visualization data structure
        trace_data = {
            "call_id": str(call.id),
            "op_name": str(call.op_name) if call.op_name else "Unknown",
            "status": "completed" if call.ended_at else "running",
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_ms": int((call.ended_at - call.started_at).total_seconds() * 1000) if call.ended_at and call.started_at else None,
            "attributes": dict(call.attributes) if call.attributes else {},
            "summary": dict(call.summary) if call.summary else {},
            "children": []
        }
        
        # Fetch child calls
        try:
            print(f"🔍 Fetching child calls for trace_id: {call.trace_id}")
            
            # Get all calls with this trace_id to build the tree
            all_calls_iter = client.calls(filter={"trace_id": call.trace_id})
            all_calls = list(all_calls_iter)
            
            print(f"✅ Found {len(all_calls)} total calls")
            
            # Build call tree
            children_map = {}
            
            for c in all_calls:
                if c.parent_id and c.parent_id == call.id:
                    if c.parent_id not in children_map:
                        children_map[c.parent_id] = []
                    
                    child_data = {
                        "call_id": str(c.id),
                        "op_name": str(c.op_name) if c.op_name else "Unknown",
                        "started_at": c.started_at.isoformat() if c.started_at else None,
                        "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                        "duration_ms": int((c.ended_at - c.started_at).total_seconds() * 1000) if c.ended_at and c.started_at else None,
                        "status": "completed" if c.ended_at else "running",
                        "summary": dict(c.summary) if c.summary else {}
                    }
                    children_map[c.parent_id].append(child_data)
            
            trace_data["children"] = children_map.get(call.id, [])
            trace_data["total_children"] = len(all_calls) - 1  # Exclude root call
            
            print(f"✅ Built tree with {len(trace_data['children'])} direct children")
            
        except Exception as e:
            print(f"⚠️ Error fetching child calls: {e}")
            import traceback
            traceback.print_exc()
            trace_data["total_children"] = 0
        
        return jsonify(trace_data)
        
    except Exception as e:
        print(f"❌ Error fetching Weave data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/debug-weave/<job_id>")
def debug_weave(job_id):
    """Debug endpoint to check Weave trace URL and job status."""
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404
    
    job_data = job_status[job_id]
    
    debug_info = {
        "job_id": job_id,
        "has_weave_url": "weave_trace_url" in job_data,
        "weave_url": job_data.get("weave_trace_url", "Not set"),
        "job_status": job_data.get("status", "Unknown"),
        "current_step": job_data.get("current_step", "Unknown"),
        "all_keys": list(job_data.keys())
    }
    
    print("🐛 Debug info for job", job_id[:8], ":")
    print(debug_info)
    
    return jsonify(debug_info)


@app.route("/git-diff/<job_id>")
def get_git_diff(job_id):
    """Get git diff for all changes in the working directory."""
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404
    
    workdir = job_status[job_id].get("work_directory")
    if not workdir or not os.path.exists(workdir):
        return jsonify({"error": "Work directory not found"}), 404
    
    try:
        diffs = {}
        
        def get_repo_diff(repo_dir, repo_name):
            """Helper function to get diff from a repository."""
            if not os.path.exists(repo_dir):
                return None
            
            try:
                print(f"📝 Checking git diff in {repo_dir}")
                
                # Method 1: Try standard git diff
                result = subprocess.run(
                    ["git", "diff", "--no-color"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    print(f"✅ Found diff using 'git diff' for {repo_name}: {len(result.stdout)} bytes")
                    return result.stdout
                
                # Method 2: Try git diff HEAD (shows all uncommitted changes)
                result = subprocess.run(
                    ["git", "diff", "HEAD", "--no-color"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    print(f"✅ Found diff using 'git diff HEAD' for {repo_name}: {len(result.stdout)} bytes")
                    return result.stdout
                
                # Method 3: Check git status to see if there are any changes
                status_result = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if status_result.returncode == 0 and status_result.stdout.strip():
                    print(f"📋 Git status shows changes for {repo_name}:")
                    print(status_result.stdout)
                    
                    # Try to get diff including untracked files
                    result = subprocess.run(
                        ["git", "diff", "--no-index", "--no-color", "/dev/null", "."],
                        cwd=repo_dir,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode in [0, 1] and result.stdout.strip():
                        print(f"✅ Found diff with untracked files for {repo_name}")
                        return result.stdout
                
                print(f"⚠️ No diff found for {repo_name}")
                return None
                
            except subprocess.TimeoutExpired:
                print(f"⏱️ Timeout getting diff for {repo_name}")
                return None
            except Exception as e:
                print(f"❌ Error getting {repo_name} diff: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Get diffs for both repositories
        r_base_dir = os.path.join(workdir, "r_base")
        r_base_diff = get_repo_diff(r_base_dir, "r_base")
        if r_base_diff:
            diffs["r_base"] = r_base_diff
        
        r_old_dir = os.path.join(workdir, "r_old")
        r_old_diff = get_repo_diff(r_old_dir, "r_old")
        if r_old_diff:
            diffs["r_old"] = r_old_diff
        
        print(f"📊 Total diffs found: {len(diffs)}")
        
        if not diffs:
            return jsonify({
                "message": "No git changes detected yet",
                "diffs": {},
                "debug": {
                    "workdir": workdir,
                    "r_base_exists": os.path.exists(r_base_dir),
                    "r_old_exists": os.path.exists(r_old_dir)
                }
            })
        
        return jsonify({
            "diffs": diffs,
            "workdir": workdir
        })
        
    except Exception as e:
        print(f"❌ Error getting git diff: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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
