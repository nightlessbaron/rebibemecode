import subprocess
import json
import sys
from typing import Optional, Dict, Any, Callable, Generator
import weave


class ReviveAgent:
    """
    A Python class that interfaces with the Cursor CLI agent using Claude 4 Sonnet.

    This class allows you to programmatically send prompts to the Cursor CLI agent
    and receive responses as strings.
    """

    @weave.op()
    def __init__(self, model: str = "auto"):
        """
        Initialize the ReviveAgent with the specified model.

        Args:
            model (str): The model to use for the Cursor CLI agent. 
                        Defaults to 'sonnet-4.5'.
        """
        self.model = model
        self._verify_cursor_cli()
        # Per-call stats
        self.last_tool_call_count = 0
        self.last_token_count = 0
        # Cumulative stats across all calls
        self.total_tool_call_count = 0
        self.total_token_count = 0
    
    def _verify_cursor_cli(self) -> None:
        """
        Verify that the Cursor CLI is installed and accessible.

        Raises:
            RuntimeError: If the Cursor CLI is not installed or not accessible.
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
    def _format_tool_call(self, tool_call: Dict[str, Any]) -> Optional[str]:
        """
        Format a tool call into a human-readable string.

        Args:
            tool_call: The tool call dictionary from the JSON stream

        Returns:
            Formatted string describing the tool call, or None if not relevant
        """
        # Check for different tool types
        if "readToolCall" in tool_call:
            path = tool_call["readToolCall"].get("args", {}).get("path", "")
            with weave.attributes({"tool_type": "read", "path": path}):
                return f"Reading file: {path}"

        elif "editToolCall" in tool_call:
            path = tool_call["editToolCall"].get("args", {}).get("path", "")
            with weave.attributes({"tool_type": "edit", "path": path}):
                return f"Editing file: {path}"

        elif "writeToolCall" in tool_call:
            path = tool_call["writeToolCall"].get("args", {}).get("path", "")
            with weave.attributes({"tool_type": "write", "path": path}):
                return f"Writing file: {path}"

        elif "shellToolCall" in tool_call:
            cmd = tool_call["shellToolCall"].get("args", {}).get("command", "")
            # Truncate long commands
            cmd_display = cmd
            if len(cmd) > 80:
                cmd_display = cmd[:77] + "..."
            with weave.attributes({"tool_type": "shell", "command": cmd}):
                return f"Running command: {cmd_display}"

        elif "lsToolCall" in tool_call:
            path = tool_call["lsToolCall"].get("args", {}).get("path", "")
            with weave.attributes({"tool_type": "ls", "path": path}):
                return f"Listing directory: {path}"

        elif "grepToolCall" in tool_call:
            pattern = tool_call["grepToolCall"].get("args", {}).get("pattern", "")
            with weave.attributes({"tool_type": "grep", "pattern": pattern}):
                return f"Searching for: {pattern}"

        elif "codebaseSearchToolCall" in tool_call:
            query = tool_call["codebaseSearchToolCall"].get("args", {}).get("query", "")
            query_display = query
            if len(query) > 60:
                query_display = query[:57] + "..."
            with weave.attributes({"tool_type": "codebase_search", "query": query}):
                return f"Searching codebase: {query_display}"

        # Return None for other tool types we don't want to display
        with weave.attributes({"tool_type": "unknown", "tool_call": str(tool_call)}):
            return None

    @weave.op()
    def run_prompt(
        self,
        prompt: str,
        timeout: int = 600,
        stream_callback: Optional[Callable[[str], None]] = None,
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
                - tool_calls: List of tool calls made by cursor-agent
                - command: The command that was executed
                - model: The model used
                - prompt_length: Length of the prompt
                - response_length: Length of the response

        Raises:
            ValueError: If the prompt is empty or None.
            RuntimeError: If the Cursor CLI command fails.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or None")

        print("--------------------------------")
        print("Running with model: ", self.model, "and prompt: ")
        print(prompt)
        print("--------------------------------")

        # Track tool calls and metrics for Weave logging
        tool_calls_log = []
        json_messages_processed = 0
        assistant_messages_count = 0
        tool_call_messages_count = 0

        try:
            # Construct the command to run the Cursor CLI with the specified model and prompt
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
            tool_call_count = 0
            token_count = 0
            
            # Read output line by line
            try:
                for line in process.stdout:
                    if line.strip():
                        try:
                            # Parse the JSON line
                            json_data = json.loads(line)
                            
                            # Extract text content from the message
                            if json_data.get("type") == "assistant":
                                message = json_data.get("message", {})
                                content = message.get("content", [])
                                if content and len(content) > 0:
                                    text = content[0].get("text", "")
                                    if text:
                                        # With --stream-partial-output, each message contains accumulated text
                                        # We need to print only the new part (delta)
                                        if text != full_response:  # Only process if text has changed
                                            if text.startswith(full_response):
                                                # Text is an extension of what we have - print the delta
                                                delta = text[len(full_response):]
                                                if delta:
                                                    print(delta, end='', flush=True)
                                                    if stream_callback:
                                                        stream_callback(delta)
                                            else:
                                                # Text doesn't start with our accumulated text
                                                # This might be the first chunk or a replacement
                                                # Print the entire text
                                                print(text, end='', flush=True)
                                                if stream_callback:
                                                    stream_callback(text)
                                            
                                            full_response = text
                            elif json_data.get("type") == "tool_call":
                                # Display tool call messages in a readable format
                                subtype = json_data.get("subtype", "")
                                tool_call = json_data.get("tool_call", {})
                                
                                if subtype == "started":
                                    # Count the tool call
                                    tool_call_count += 1
                                    
                                    # Extract tool information
                                    tool_info = self._format_tool_call(tool_call)
                                    if tool_info:
                                        msg = f"\n🔧 {tool_info}\n"
                                        print(msg, flush=True)
                                        if stream_callback:
                                            stream_callback(msg)
                            
                            # Track token usage if provided
                            usage = json_data.get("usage", {})
                            if "total_tokens" in usage:
                                token_count = usage["total_tokens"]
                            elif "completion_tokens" in usage:
                                token_count += usage.get("completion_tokens", 0)
                                            
                        except json.JSONDecodeError:
                            # If it's not valid JSON, skip it
                            continue
                
                # Estimate tokens if not provided by the stream
                if token_count == 0 and full_response:
                    # Rough estimate: ~4 characters per token (common heuristic)
                    token_count = len(full_response) // 4
                
                # Store stats in instance variables
                self.last_tool_call_count = tool_call_count
                self.last_token_count = token_count
                
                # Accumulate to total stats
                self.total_tool_call_count += tool_call_count
                self.total_token_count += token_count
                
                # Display stats for this call
                stats_msg = f"\n📊 This call: {tool_call_count} tool calls | ~{token_count} tokens | Total so far: {self.total_tool_call_count} tool calls | ~{self.total_token_count} tokens\n"
                print(stats_msg)
                if stream_callback:
                    stream_callback(stats_msg)
                
                # Wait for the process to complete
                process.wait(timeout=timeout)
                print()  # Add newline after streaming
                
                if process.returncode != 0:
                    stderr = process.stderr.read()
                    raise RuntimeError(f"Cursor CLI command failed: {stderr}")
                
                return full_response
                
            except subprocess.TimeoutExpired:
                process.kill()
                raise RuntimeError(f"Command timed out after {timeout} seconds")
            
        except subprocess.TimeoutExpired as e:
            with weave.attributes(
                {"error_type": "timeout_expired", "timeout_seconds": timeout}
            ):
                raise RuntimeError(f"Command timed out after {timeout} seconds") from e
        except FileNotFoundError as e:
            with weave.attributes(
                {"error_type": "cursor_cli_not_found", "command": command[0]}
            ):
                raise RuntimeError("Cursor CLI not found") from e
        except Exception as e:
            with weave.attributes(
                {"error_type": "unexpected_error", "error_message": str(e)}
            ):
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
        Change the model used by the agent.

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
    
    def reset_stats(self) -> None:
        """
        Reset all statistics counters (both per-call and cumulative).
        """
        self.last_tool_call_count = 0
        self.last_token_count = 0
        self.total_tool_call_count = 0
        self.total_token_count = 0
    
    def print_total_stats(self) -> None:
        """
        Print a summary of total statistics.
        """
        print("\n" + "="*80)
        print(f"📊 TOTAL STATS FOR THIS SESSION")
        print("="*80)
        print(f"Total Tool Calls: {self.total_tool_call_count}")
        print(f"Total Tokens: ~{self.total_token_count}")
        print("="*80 + "\n")


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
