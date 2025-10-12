#!/usr/bin/env python3
"""
python3 classes/simple_revive_agent_test.py
"""

from revive_agent import ReviveAgent


def test_summarize_project():
    """Simple test to summarize this project using ReviveAgent."""

    print("Testing ReviveAgent with 'summarize this project' command...")
    print("-" * 60)

    try:
        # Initialize the agent
        agent = ReviveAgent(model='auto')
        print(f"✓ ReviveAgent initialized with model: {agent.get_model()}")

        # Simple test prompt
        prompt = "Summarize this project"
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


if __name__ == "__main__":
    success = test_summarize_project()
    if not success:
        print("\nNote: Make sure CLI is installed:")
        print("curl https://cursor.com/install -fsS | bash")

    # success = test_shell_execution()
    # if not success:
    #     print("\nNote: Make sure CLI is installed:")
    #     print("curl https://cursor.com/install -fsS | bash")
