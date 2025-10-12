import re
import sys

from cursor_cli_agent import CursorCLIAgent

class IterativeLoop:

    def __init__(self, model: str = 'sonnet-4.5', timeout: int = 120, max_iterations: int = 5):

        self.agent = CursorCLIAgent(model=model)
        self.timeout = timeout
        self.max_iterations = max_iterations
        self.iteration_count = 0
        
    def activate_env_and_run_script(self, env_name: str = 'env_r_base', script_path: str = 'run test_old.sh'):
        
        print("=" * 80)
        print(f"Task 6: Activate {env_name} and Execute {script_path}")
        print("=" * 80)
        print()
        
        try:
            print(f"✓ CursorCLIAgent initialized with model: {self.agent.get_model()}")
            
            # Construct the prompt to activate the conda environment and run the script
            prompt = f"""
Activate the conda environment called '{env_name}' and execute the file '{script_path}'.

Please perform the following steps:
1. Activate the conda environment: conda activate {env_name}
2. Execute the shell script: bash "{script_path}" (or ./"{script_path}" if it's executable)
3. Show the full output including any errors

Make sure to handle any errors that might occur during activation or execution.
"""
            
            print("Sending prompt to Cursor CLI agent...")
            print("-" * 80)
            print(f"Prompt: {prompt.strip()}")
            print("-" * 80)
            print()
            
            # Run the prompt through the Cursor CLI agent
            response = self.agent.run_prompt(prompt, timeout=self.timeout)
            
            print("Response from Cursor CLI agent:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            print()
            
            # Check if there are errors in the response
            if self.detect_errors(response):
                print("⚠ Errors detected in execution!")
                error_details = self.extract_error_details(response)
                
                print("\nExtracted Error Details:")
                print("-" * 80)
                print(error_details)
                print("-" * 80)
                
                # Attempt to fix the errors iteratively
                fix_success = self.fix_errors(error_details)
                
                if fix_success:
                    print("\n✓ Task completed successfully after fixing errors!")
                    return True, "No errors"
                else:
                    print("\n✗ Unable to resolve errors after all iterations")
                    return False, error_details
            else:
                print("✓ Task completed successfully with no errors!")
                return True, "No errors"
            
        except Exception as e:
            print(f"✗ Task failed with exception: {e}")
            print("Troubleshooting tips:")
            print("1. Make sure Cursor CLI is installed: curl https://cursor.com/install -fsS | bash")
            print(f"2. Verify that the '{env_name}' conda environment exists: conda env list")
            print(f"3. Check that '{script_path}' exists in the expected location")
            return False
    
    def detect_errors(self, response: str) -> bool:

        # Common error indicators
        error_patterns = [
            r'error:',
            r'Error:',
            r'ERROR:',
            r'failed',
            r'Failed',
            r'FAILED',
            r'exception',
            r'Exception',
            r'traceback',
            r'Traceback',
            r'not found',
            r'No such file',
            r'cannot find',
            r'command not found',
            r'syntax error',
            r'SyntaxError',
            r'ImportError',
            r'ModuleNotFoundError',
            r'NameError',
            r'TypeError',
            r'ValueError',
        ]
        
        response_lower = response.lower()
        
        for pattern in error_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
                
        return False
    
    def extract_error_details(self, response: str) -> str:
        return response
    
    def fix_errors(self, error_details: str) -> bool:
        self.iteration_count += 1
        
        print("\n" + "!" * 80)
        print(f"ITERATION {self.iteration_count}/{self.max_iterations}: Errors detected, attempting to fix...")
        print("!" * 80)
        
        if self.iteration_count > self.max_iterations:
            print(f"✗ Maximum iterations ({self.max_iterations}) reached. Stopping.")
            return False
        
        # Construct a prompt to fix the errors
        fix_prompt = f"""
The previous execution encountered errors. Please analyze and fix the code in R_old.

ERROR DETAILS:
{error_details}

INSTRUCTIONS:
1. Carefully analyze the error messages and identify the root cause
2. Fix the code in R_old to resolve these errors
3. IMPORTANT: Only add dependencies or make modifications to env_r_base if absolutely necessary
4. Prefer fixing the code logic rather than changing the environment
5. If you must add dependencies, clearly state why they are essential
6. After making fixes, re-run the script to verify it works

Please make the necessary fixes and execute the script again.
"""
        
        print("Sending fix prompt to Cursor CLI agent...")
        print("-" * 80)
        print(f"Fix Prompt: {fix_prompt.strip()}")
        print("-" * 80)
        print()
        
        try:
            response = self.agent.run_prompt(fix_prompt, timeout=self.timeout)
            
            print("Response from Cursor CLI agent:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            print()
            
            # Check if the fix introduced new errors
            if self.detect_errors(response):
                print("⚠ Errors still present after fix attempt")
                new_error_details = self.extract_error_details(response)
                # Recursively try to fix again
                return self.fix_errors(new_error_details)
            else:
                print("✓ Errors resolved successfully!")
                return True
                
        except Exception as e:
            print(f"✗ Error during fix attempt: {e}")
            return False
    
    def run(self):
        return self.activate_env_and_run_script()


def main():
    loop = IterativeLoop()
    success = loop.run()
    
    if success:
        print("\n✓ All operations completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Operations failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

