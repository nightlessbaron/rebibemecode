import subprocess
from typing import Optional, Dict, Any, Callable
import weave
from classes.clean_logger import stream_json_output, StreamCollector
from termcolor import cprint

class ReviveAgent:
    """
    A Python class that interfaces with the CLI agent using Claude 4 Sonnet.

    This class allows you to programmatically send prompts to the CLI agent
    and receive responses as strings.
    """
    @weave.op()
    def __init__(self, model: str):
        """
        Initialize the ReviveAgent with the specified model.

        Args:
            model (str): The model to use for the CLI agent. 
        """
        self.model = model
        self._verify_cli()
        self.total_tokens_used = 0
        self.total_tool_calls_used = 0

    # In destructor, print the total stats
    def __del__(self):
        cprint("-"*80, "green")
        cprint("Agent stats before destruction", "green")
        cprint(f"\tTotal tokens used: {self.total_tokens_used}", "green")
        cprint(f"\tTotal tool calls used: {self.total_tool_calls_used}", "green")
        cprint("-"*80, "green")
    
    def _verify_cli(self) -> None:
        """
        Verify that the CLI is installed and accessible.

        Raises:
            RuntimeError: If the CLI is not installed or not accessible.
        """
        try:
            result = subprocess.run(
                ["cursor-agent", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version = result.stdout.strip()
            with weave.attributes({"cursor_cli_version": version}):
                print(f"Cursor CLI detected: {version}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            with weave.attributes({"error": "cursor_cli_not_found"}):
                raise RuntimeError(
                    "Cursor CLI not found. Please install it using:\n"
                    "curl https://cursor.com/install -fsS | bash"
                ) from e

    @weave.op()
    def run_prompt(
        self,
        prompt: str,
        timeout: int = 600,
        stream_callback: Optional[Callable[[str], None]] = None,
        summarize_reduce: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a prompt through the underlying agent and return the response.

        Args:
            prompt (str): The input prompt to send to the agent.
            timeout (int): Maximum time in seconds to wait for response. Defaults to 600.
            stream_callback (callable, optional): A callback function to receive streaming text chunks.

        Returns:
            dict: Dictionary containing:
                - response: The complete response text
                - tool_calls: List of tool calls made by the CLI agent
                - command: The command that was executed
                - model: The model used
                - prompt_length: Length of the prompt
                - response_length: Length of the response

        Raises:
            ValueError: If the prompt is empty or None.
            RuntimeError: If the CLI command fails.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or None")
        
        if summarize_reduce:
            print("--------------------------------")
            print("Running with model: ", self.model, "and prompt: ")
            print(prompt)
            print("--------------------------------")
        
        try:
            # Construct the command to run the CLI with the specified model and prompt
            command = [
                "cursor-agent",
                "chat",
                "--print",
                "--model",
                self.model,
                "--output-format",
                "stream-json",
                "--stream-partial-output",
                prompt.strip(),
            ]
            
            # Use Popen to capture streaming output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            full_response = ""
            # Read output line by line
            try:
                collector = StreamCollector()
                data = stream_json_output(process, collector.callback)
                full_response = collector.full_response                 
                
                # Wait for the process to complete
                process.wait(timeout=timeout)
                print()  # Add newline after streaming
                
                if process.returncode != 0:
                    stderr = process.stderr.read()
                    raise RuntimeError(f"Agent CLI command failed: {stderr}")
                
                if summarize_reduce:
                    self.total_tokens_used += data["tokens"]
                    self.total_tool_calls_used += data["tool_calls"]
                    self.summarize_reduce(prompt, full_response, "./")
                
                return full_response
                
            except subprocess.TimeoutExpired:
                process.kill()
                raise RuntimeError(f"Command timed out after {timeout} seconds")
            
        except Exception as e:
            raise RuntimeError(f"Unexpected error occurred: {str(e)}") from e

    @weave.op()
    def run_prompt_with_context(
        self, prompt: str, context: Optional[Dict[str, Any]] = None, timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Run a prompt with additional context through the underlying agent.

        Args:
            prompt (str): The input prompt to send to the agent.
            context (dict, optional): Additional context to include with the prompt.
            timeout (int): Maximum time in seconds to wait for response. Defaults to 60.

        Returns:
            dict: The response dictionary from run_prompt.
        """
        if context:
            # Format the context as a string and prepend to the prompt
            context_str = "\n".join(
                [f"{key}: {value}" for key, value in context.items()]
            )
            formatted_prompt = f"Context:\n{context_str}\n\nPrompt:\n{prompt}"
        else:
            formatted_prompt = prompt

        with weave.attributes(
            {
                "has_context": context is not None,
                "context_keys": list(context.keys()) if context else [],
            }
        ):
            return self.run_prompt(formatted_prompt, timeout)

    @weave.op()
    def set_model(self, model: str) -> None:
        """
        Change the model used by the ReviceCLI agent.

        Args:
            model (str): The new model to use.
        """
        old_model = self.model
        self.model = model
        with weave.attributes({"old_model": old_model, "new_model": model}):
            pass

    @weave.op()
    def get_model(self) -> str:
        """
        Get the current model being used.

        Returns:
            str: The current model name.
        """
        return self.model
    
    def get_last_stats(self) -> Dict[str, int]:
        """
        Get statistics from the last run_prompt call.
        
        Returns:
            dict: Dictionary containing 'tool_calls' and 'tokens' counts for the last call
        """
        return {
            'tool_calls': self.last_tool_call_count,
            'tokens': self.last_token_count
        }
    
    def get_total_stats(self) -> Dict[str, int]:
        """
        Get cumulative statistics across all run_prompt calls.
        
        Returns:
            dict: Dictionary containing total 'tool_calls' and 'tokens' counts
        """
        return {
            'tool_calls': self.total_tool_call_count,
            'tokens': self.total_token_count
        }

    def summarize_reduce(self, prompt, response, global_dir):
        """
        Summarize the mistakes made by the agent and reduce them to a log of mistakes.
        """
        global_prompt = f"""
        You are a mistake summarizer. 
        You need to summarize mistakes related code integration and depencency resolution only, else skip it.
        You will be given a prompt and a response, which you need to use and identify mistakes the agentic transaction made.

        1. If a file {global_dir}/mistake_log.md exists, read it and understad what mistakes are already logged
        2. Read the file {global_dir}/mistake_log_dump.txt, and try to understand what were the key mistakes that were made in that agentic transaction
        3. Make sure to conslidate all mistakes in the {global_dir}/mistake_log.md file at the end, and only keep a max of 10 mistakes
           The mistakes should only be focussed on code integration and depencency resolution only, keep only medium-high value mistakes
           In case something took a long time to fix (>2 tries), make sure to record it as a mistake (so you can shortcut it later)
           Try not to keep this file empty (0 mistakes), as we really want to self improve over iterations
           Format should be: Mistake: <mistake> | How to fix: <how to fix>
        """
        # Put the mistake lot in {global_dir}/mistake_log_dump.txt
        with open(f"{global_dir}/mistake_log_dump.txt", "w") as f:
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Response: {response}\n")

        # Run the prompt
        self.run_prompt(global_prompt, summarize_reduce=False)


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize the Revive agent
        agent = ReviveAgent()

        # Test with a simple prompt
        test_prompt = (
            "Write a simple Python function that calculates the factorial of a number."
        )
        print("Sending prompt to agent...")
        print(f"Prompt: {test_prompt}")
        print("-" * 80)

        response = agent.run_prompt(test_prompt)
        print("Response from agent:")
        print(response)
        print("-" * 80)
        
        # Get stats from the last run
        stats = agent.get_last_stats()
        print(f"\nLast run stats: {stats['tool_calls']} tool calls, {stats['tokens']} tokens")
        print("-" * 80)

        # Test with context
        context = {
            "language": "Python",
            "style": "Clean and well-documented",
            "requirements": "Include error handling",
        }

        context_prompt = "Create a function to read a JSON file"
        print(f"\nSending prompt with context...")
        print(f"Prompt: {context_prompt}")
        print(f"Context: {context}")
        print("-" * 80)

        response_with_context = agent.run_prompt_with_context(context_prompt, context)
        print("Response from agent (with context):")
        print(response_with_context)

    except Exception as e:
        print(f"Error: {e}")
