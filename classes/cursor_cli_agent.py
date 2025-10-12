import subprocess
import json
import sys
from typing import Optional, Dict, Any, Callable, Generator


class CursorCLIAgent:
    """
    A Python class that interfaces with the Cursor CLI agent using Claude 4 Sonnet.
    
    This class allows you to programmatically send prompts to the Cursor CLI agent
    and receive responses as strings.
    """
    
    def __init__(self, model: str = 'auto'):
        """
        Initialize the CursorCLIAgent with the specified model.
        
        Args:
            model (str): The model to use for the Cursor CLI agent. 
                        Defaults to 'sonnet-4.5'.
        """
        self.model = model
        self._verify_cursor_cli()
    
    def _verify_cursor_cli(self) -> None:
        """
        Verify that the Cursor CLI is installed and accessible.
        
        Raises:
            RuntimeError: If the Cursor CLI is not installed or not accessible.
        """
        try:
            result = subprocess.run(
                ['cursor-agent', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Cursor CLI detected: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "Cursor CLI not found. Please install it using:\n"
                "curl https://cursor.com/install -fsS | bash"
            ) from e
    
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
            return f"Reading file: {path}"
        
        elif "editToolCall" in tool_call:
            path = tool_call["editToolCall"].get("args", {}).get("path", "")
            return f"Editing file: {path}"
        
        elif "writeToolCall" in tool_call:
            path = tool_call["writeToolCall"].get("args", {}).get("path", "")
            return f"Writing file: {path}"
        
        elif "shellToolCall" in tool_call:
            cmd = tool_call["shellToolCall"].get("args", {}).get("command", "")
            # Truncate long commands
            if len(cmd) > 80:
                cmd = cmd[:77] + "..."
            return f"Running command: {cmd}"
        
        elif "lsToolCall" in tool_call:
            path = tool_call["lsToolCall"].get("args", {}).get("path", "")
            return f"Listing directory: {path}"
        
        elif "grepToolCall" in tool_call:
            pattern = tool_call["grepToolCall"].get("args", {}).get("pattern", "")
            return f"Searching for: {pattern}"
        
        elif "codebaseSearchToolCall" in tool_call:
            query = tool_call["codebaseSearchToolCall"].get("args", {}).get("query", "")
            if len(query) > 60:
                query = query[:57] + "..."
            return f"Searching codebase: {query}"
        
        # Return None for other tool types we don't want to display
        return None
    
    def run_prompt(self, prompt: str, timeout: int = 600, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Run a prompt through the Cursor CLI agent and return the response.
        
        Args:
            prompt (str): The input prompt to send to the Cursor CLI agent.
            timeout (int): Maximum time in seconds to wait for response. Defaults to 600.
            stream_callback (callable, optional): A callback function to receive streaming text chunks.
        
        Returns:
            str: The complete response from the Cursor CLI agent as a string.
            
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
        
        try:
            # Construct the command to run the Cursor CLI with the specified model and prompt
            command = [
                'cursor-agent',
                'chat',
                '--print',
                '--model', self.model,
                '--output-format', 'stream-json',
                '--stream-partial-output',
                prompt.strip()
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
                                    # Extract tool information
                                    tool_info = self._format_tool_call(tool_call)
                                    if tool_info:
                                        msg = f"\n🔧 {tool_info}\n"
                                        print(msg, flush=True)
                                        if stream_callback:
                                            stream_callback(msg)
                                            
                        except json.JSONDecodeError:
                            # If it's not valid JSON, skip it
                            continue
                
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
            raise RuntimeError(f"Command timed out after {timeout} seconds") from e
        except FileNotFoundError as e:
            raise RuntimeError("Cursor CLI not found") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error occurred: {str(e)}") from e
    
    def run_prompt_with_context(self, prompt: str, context: Optional[Dict[str, Any]] = None, timeout: int = 60) -> str:
        """
        Run a prompt with additional context through the Cursor CLI agent.
        
        Args:
            prompt (str): The input prompt to send to the Cursor CLI agent.
            context (dict, optional): Additional context to include with the prompt.
            timeout (int): Maximum time in seconds to wait for response. Defaults to 60.
        
        Returns:
            str: The response from the Cursor CLI agent as a string.
        """
        if context:
            # Format the context as a string and prepend to the prompt
            context_str = "\n".join([f"{key}: {value}" for key, value in context.items()])
            formatted_prompt = f"Context:\n{context_str}\n\nPrompt:\n{prompt}"
        else:
            formatted_prompt = prompt
            
        return self.run_prompt(formatted_prompt, timeout)
    
    def set_model(self, model: str) -> None:
        """
        Change the model used by the Cursor CLI agent.
        
        Args:
            model (str): The new model to use.
        """
        self.model = model
    
    def get_model(self) -> str:
        """
        Get the current model being used.
        
        Returns:
            str: The current model name.
        """
        return self.model


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize the Cursor CLI agent
        agent = CursorCLIAgent()
        
        # Test with a simple prompt
        test_prompt = "Write a simple Python function that calculates the factorial of a number."
        print("Sending prompt to Cursor CLI agent...")
        print(f"Prompt: {test_prompt}")
        print("-" * 80)
        
        response = agent.run_prompt(test_prompt)
        print("Response from Cursor CLI agent:")
        print(response)
        print("-" * 80)
        
        # Test with context
        context = {
            "language": "Python",
            "style": "Clean and well-documented",
            "requirements": "Include error handling"
        }
        
        context_prompt = "Create a function to read a JSON file"
        print(f"\nSending prompt with context...")
        print(f"Prompt: {context_prompt}")
        print(f"Context: {context}")
        print("-" * 80)
        
        response_with_context = agent.run_prompt_with_context(context_prompt, context)
        print("Response from Cursor CLI agent (with context):")
        print(response_with_context)
        
    except Exception as e:
        print(f"Error: {e}")
