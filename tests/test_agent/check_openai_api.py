"""Simple script to test OpenAI API connectivity."""

import sys
from openai import OpenAI

# Use the same API key from the script
api_key = "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"


def check_api_connection():
    """Test a simple OpenAI API connection."""
    print("Testing OpenAI API connection...")

    try:
        # Initialize the client with the API key
        client = OpenAI(api_key=api_key)

        # Make a simple request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a simpler model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"},
            ],
            max_tokens=10,  # Request minimal tokens for a quick test
        )

        # If we get here, the connection worked
        print("SUCCESS: API connection established!")
        print(f"Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        # Print detailed error information
        print(f"ERROR: {type(e).__name__}: {str(e)}")

        # Check for common error types and provide more helpful messages
        if "invalid_api_key" in str(e).lower() or "authentication" in str(e).lower():
            print("\nPossible cause: The API key may be invalid or expired.")
            print("Solution: Obtain a new API key from the OpenAI dashboard.")

        elif "insufficient_quota" in str(e).lower():
            print("\nPossible cause: Your OpenAI account may be out of credits.")
            print(
                "Solution: Check your usage and billing information in the OpenAI dashboard."
            )

        elif "connection" in str(e).lower():
            print("\nPossible cause: Network connectivity issue.")
            print("Solution: Check your internet connection and firewall settings.")
            print("          Some networks block OpenAI API calls.")
            print("          Try using a different network or VPN.")

        return False


if __name__ == "__main__":
    success = check_api_connection()
    sys.exit(0 if success else 1)
