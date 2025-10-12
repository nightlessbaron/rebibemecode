#!/usr/bin/env python3
"""
python3 classes/simple_revive_agent_test.py
"""
import sys
sys.path.append("./")
from revive_agent import ReviveAgent, run_prompt_parallel
import time


def test_summarize_project():
    """Simple test to summarize this project using ReviveAgent."""

    print("Testing ReviveAgent with 'summarize this project' command...")
    print("-" * 60)

    try:
        # Initialize the agent
        agent = ReviveAgent(model='auto')
        print(f"✓ ReviveAgent initialized with model: {agent.get_model()}")

        # Simple test prompt
        prompt = "Quickly summarize this project"
        print(f"Sending prompt: '{prompt}'")
        print("-" * 60)

        # Run the prompt
        response = agent.run_prompt(prompt)

        print("Response:")
        print(response)
        print("-" * 60)
        print("✓ Test completed successfully!")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

    return True


def test_shell_execution():
    """Simple test to execute a shell script."""
    print("Testing ReviveAgent with 'execute a shell script' command...")
    print("-" * 60)

    try:
        agent = ReviveAgent()
        print(f"✓ ReviveAgent initialized with model: {agent.get_model()}")

        prompt = "Write a simple python3 script to print 'Hello, World!'. Run it and verify it prints 'Hello, World!'."
        print(f"Sending prompt: '{prompt}'")
        print("-" * 60)

        response = agent.run_prompt(prompt)
        print("Response:")
        print(response)
        print("-" * 60)
        print("✓ Test completed successfully!")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

    return True


def test_parallel_execution():
    """Test the parallel execution function with timeout."""
    print("Testing run_prompt_parallel function...")
    print("-" * 60)

    try:
        # Test basic parallel execution
        start_time = time.time()
        
        handle = run_prompt_parallel(
            prompt="Write a simple Hello World script in Python and execute it",
            model="auto",
            summarize_reduce=False,  # Skip summarize for faster execution
            timeout=60  # 1 minute timeout for this test
        )
        
        print("✓ Function returned immediately (non-blocking)")
        
        # Wait for completion
        result = handle.get_result(wait=True)
        
        execution_time = time.time() - start_time
        
        print(f"✓ Parallel execution completed in {execution_time:.2f} seconds")
        print(f"Success: {result['success']}")
        
        if result['success']:
            print(f"Result preview: {result['result'][:200]}..." if len(result['result']) > 200 else result['result'])
            print(f"Stats: {result['stats']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Timeout: {result['timeout']}")
            
        return result['success']

    except Exception as e:
        print(f"✗ Parallel test failed: {e}")
        return False


def test_parallel_timeout():
    """Test the parallel execution timeout functionality."""
    print("Testing run_prompt_parallel timeout functionality...")
    print("-" * 60)

    try:
        # Test with very short timeout to trigger timeout
        start_time = time.time()
        
        handle = run_prompt_parallel(
            prompt="Analyze this entire repository structure in great detail and create a comprehensive documentation",
            model="auto",
            summarize_reduce=True,
            timeout=100 # Very short timeout to test timeout handling
        )
        
        print("✓ Function returned immediately (non-blocking)")
        
        # Wait for completion or timeout
        result = handle.get_result(wait=True)
        
        execution_time = time.time() - start_time
        
        print(f"✓ Timeout test completed in {execution_time:.2f} seconds")
        print(f"Success: {result['success']}")
        print(f"Timeout occurred: {result['timeout']}")
        
        if result['timeout']:
            print("✓ Timeout mechanism working correctly!")
            return True
        elif result['success']:
            print("✓ Task completed before timeout (also valid)")
            return True
        else:
            print(f"Error: {result['error']}")
            return False

    except Exception as e:
        print(f"✗ Timeout test failed: {e}")
        return False


if __name__ == "__main__":
    print("=== ReviveAgent Tests ===\n")
    
    test_summarize_project()
    # test_parallel_execution()
    # test_parallel_timeout()