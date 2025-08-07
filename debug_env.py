#!/usr/bin/env python3
"""
Debug environment variables loading
"""
import os
from dotenv import load_dotenv

print("🔍 Debugging Environment Variables")
print("=" * 40)

# Check if .env file exists
env_file_exists = os.path.exists('.env')
print(f"1. .env file exists: {env_file_exists}")

if env_file_exists:
    # Show .env file contents (first few lines only for security)
    with open('.env', 'r') as f:
        lines = f.readlines()[:3]  # Only first 3 lines for security
    print(f"2. .env file has {len(lines)} lines (showing first 3):")
    for i, line in enumerate(lines, 1):
        # Hide actual API key values for security
        if '=' in line:
            key, value = line.split('=', 1)
            value_preview = value[:10] + "..." if len(value) > 10 else value
            print(f"   Line {i}: {key}={value_preview}")
        else:
            print(f"   Line {i}: {line.strip()}")

# Load environment variables
print("\n3. Loading .env file...")
load_dotenv()

# Check what got loaded
required_keys = ['GEMINI_API_KEY', 'GROK_API_KEY', 'OPENAI_API_KEY']
print("4. Checking API keys:")

for key in required_keys:
    value = os.getenv(key)
    if value:
        print(f"   ✅ {key}: Found (length: {len(value)})")
    else:
        print(f"   ❌ {key}: Not found")

print("\n💡 Expected .env format:")
print("GEMINI_API_KEY=your_actual_key_here")
print("GROK_API_KEY=your_actual_key_here") 
print("OPENAI_API_KEY=your_actual_key_here")
print("\n(No quotes, no spaces around =)")
