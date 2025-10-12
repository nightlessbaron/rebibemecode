import subprocess
import json
from typing import Optional, Dict, Any


class CursorCLIAgent:
    """
    A Python class that interfaces with the Cursor CLI agent using Claude 4 Sonnet.
    
    This class allows you to programmatically send prompts to the Cursor CLI agent
    and receive responses as strings.
    """
    
    def __init__(self, model: str = 'sonnet-4.5'):
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
    
    def run_prompt(self, prompt: str, timeout: int = 600) -> str:
        """
        Run a prompt through the Cursor CLI agent and return the response.
        
        Args:
            prompt (str): The input prompt to send to the Cursor CLI agent.
            timeout (int): Maximum time in seconds to wait for response. Defaults to 60.
        
        Returns:
            str: The response from the Cursor CLI agent as a string.
            
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
            
            # Execute the command and capture the output
            result = subprocess.run(
                command,
                check=True,
                timeout=timeout
            )
            return result
            
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Command timed out after {timeout} seconds") from e
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else "Unknown error"
            raise RuntimeError(f"Cursor CLI command failed: {error_msg}") from e
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
