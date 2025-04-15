import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get all environment variables
env_vars = dict(os.environ)

# Filter out sensitive information
filtered_env = {}
for key, value in env_vars.items():
    # Don't include API keys or tokens in the output
    if 'key' in key.lower() or 'token' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
        filtered_env[key] = f"[REDACTED] (Length: {len(value)})"
    else:
        filtered_env[key] = value

# Print environment variables
print("Environment Variables:")
print(json.dumps(filtered_env, indent=2))

# Specifically check for Anthropic API key
anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
vercel_anthropic_key = os.environ.get('VERCEL_ANTHROPIC_API_KEY')

print("\nAPI Key Status:")
print(f"ANTHROPIC_API_KEY present: {bool(anthropic_key)}")
print(f"VERCEL_ANTHROPIC_API_KEY present: {bool(vercel_anthropic_key)}")

# Test Flask environment
print("\nFlask Environment:")
flask_env = os.environ.get('FLASK_ENV')
flask_debug = os.environ.get('FLASK_DEBUG')
print(f"FLASK_ENV: {flask_env}")
print(f"FLASK_DEBUG: {flask_debug}")

# Test Python environment
print("\nPython Environment:")
print(f"Python Version: {os.environ.get('PYTHONVERSION', 'Not set')}")
print(f"Python Path: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"Python Unbuffered: {os.environ.get('PYTHONUNBUFFERED', 'Not set')}")
