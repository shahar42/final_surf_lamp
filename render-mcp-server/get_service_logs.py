#!/usr/bin/env python3
"""
Surf Lamp Service Logs Tool
Simple wrapper around Render API to get logs for both background processor and web service
"""

import os
import subprocess
import json
import sys
from datetime import datetime

def load_env():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    return env_vars

def get_service_logs(service_type='background', limit=20, json_output=False):
    """Get logs for the specified service type"""
    env_vars = load_env()

    required_vars = ['RENDER_API_KEY', 'OWNER_ID']

    if service_type == 'background':
        service_id_var = 'BACKGROUND_SERVICE_ID'
    elif service_type == 'web':
        service_id_var = 'SERVICE_ID'
    else:
        print(f"Error: Unknown service type '{service_type}'. Use 'background' or 'web'", file=sys.stderr)
        return None

    required_vars.append(service_id_var)

    for var in required_vars:
        if var not in env_vars:
            print(f"Error: {var} not found in .env file", file=sys.stderr)
            return None

    api_key = env_vars['RENDER_API_KEY']
    owner_id = env_vars['OWNER_ID']
    service_id = env_vars[service_id_var]

    # Build curl command
    url = f"https://api.render.com/v1/logs?ownerId={owner_id}&resource={service_id}&limit={limit}"

    cmd = [
        'curl',
        '-H', f'Authorization: Bearer {api_key}',
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if json_output:
            return result.stdout

        # Parse and format the output
        data = json.loads(result.stdout)

        if 'logs' not in data:
            print("No logs found in response")
            return None

        service_name = "Background Service" if service_type == 'background' else "Web Service"
        print(f"🔍 {service_name} Logs (Latest {len(data['logs'])} entries)")
        print("=" * 60)

        # Reverse to show oldest first (chronological order)
        for log in reversed(data['logs']):
            timestamp = log['timestamp']
            message = log['message']
            level = 'info'

            # Extract level from labels
            for label in log.get('labels', []):
                if label['name'] == 'level':
                    level = label['value']
                    break

            # Format timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M:%S')

            # Color coding based on level
            level_emoji = {
                'info': '💬',
                'error': '❌',
                'warn': '⚠️',
                'debug': '🔍'
            }.get(level, '📝')

            print(f"{level_emoji} {time_str} | {message}")

        if data.get('hasMore'):
            print("\n📋 More logs available (use --limit to get more)")

        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Error calling Render API: {e}", file=sys.stderr)
        print(f"Response: {e.stdout}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        return None

def get_both_services_logs(limit=20):
    """Get logs from both services side by side"""
    print("🚀 SURF LAMP SERVICES LOGS")
    print("=" * 80)

    # Get background service logs
    print("\n🔧 BACKGROUND PROCESSOR:")
    bg_result = get_service_logs('background', limit=limit//2, json_output=False)

    print("\n" + "=" * 80)

    # Get web service logs
    print("\n🌐 WEB SERVICE:")
    web_result = get_service_logs('web', limit=limit//2, json_output=False)

    return bg_result and web_result

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Get surf lamp service logs from Render')
    parser.add_argument('--service', choices=['background', 'web', 'both'], default='background',
                       help='Which service logs to get (default: background)')
    parser.add_argument('--limit', type=int, default=20, help='Number of log entries to retrieve (default: 20)')
    parser.add_argument('--json', action='store_true', help='Output raw JSON response')

    args = parser.parse_args()

    if args.service == 'both':
        if args.json:
            print("Error: --json not supported with --service both", file=sys.stderr)
            sys.exit(1)
        result = get_both_services_logs(limit=args.limit)
    else:
        result = get_service_logs(service_type=args.service, limit=args.limit, json_output=args.json)

    if result is None:
        sys.exit(1)

    if args.json:
        print(result)

if __name__ == '__main__':
    main()