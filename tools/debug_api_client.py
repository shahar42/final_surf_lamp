import json
import sys
import getpass
import time

try:
    import requests
except ImportError:
    print("Error: The 'requests' library is not installed.")
    print("Please install it using: pip install requests")
    sys.exit(1)

class SurfLampClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.logged_in = False

    def login(self, email, password):
        url = f"{self.base_url}/login"
        print(f"Attempting login at: {url}")
        
        # First, GET the login page to potentially get a CSRF token (if Flask-WTF is strict)
        # Though usually session cookie is enough for simple Flask-Login setups unless CSRF is strictly enforced via token
        try:
            r = self.session.get(url)
            if r.status_code != 200:
                print(f"Failed to load login page. Status: {r.status_code}")
                return False
            
            # Simple form data payload as Flask-WTF expects
            # Note: If CSRF token is required, we'd need to parse it from HTML.
            # For this decoupled script, we'll try sending just credentials first.
            # If it fails due to CSRF, we might need to parse the token.
            
            # Let's try to find csrf_token if present in cookies or HTML
            csrf_token = None
            if 'csrf_token' in r.cookies:
                csrf_token = r.cookies['csrf_token']
            
            payload = {
                'email': email,
                'password': password
            }
            if csrf_token:
                payload['csrf_token'] = csrf_token

            # Flask-WTF forms often put csrf_token in hidden input
            # Parsing HTML with regex to find it if needed (skipping for now to keep it simple)

            response = self.session.post(url, data=payload)
            
            # Check if we were redirected to dashboard (indicating success)
            if response.url.endswith('/dashboard'):
                print("Login successful!")
                self.logged_in = True
                return True
            elif "Invalid email or password" in response.text:
                 print("Login failed: Invalid credentials.")
            else:
                # If we are still on login page, it failed
                if '/login' in response.url:
                     print("Login failed (Check credentials or CSRF token requirement).")
                else:
                    print(f"Login outcome uncertain. Current URL: {response.url}")
                    self.logged_in = True # Assume success if redirected elsewhere
            return self.logged_in

        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return False

    def get_arduino_data(self, arduino_id):
        url = f"{self.base_url}/api/arduino/{arduino_id}/data"
        print(f"\nRequesting: {url}")
        try:
            response = self.session.get(url)
            self._print_response(response)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def update_location(self, new_location):
        if not self.logged_in:
            print("Warning: You are not logged in. This request will likely fail (401/403).")
        
        url = f"{self.base_url}/update-location"
        payload = {'location': new_location}
        print(f"\nPOSTing to: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = self.session.post(url, json=payload)
            self._print_response(response)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def get_chat_status(self):
        url = f"{self.base_url}/api/chat/status"
        print(f"\nRequesting: {url}")
        try:
            response = self.session.get(url)
            self._print_response(response)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def _print_response(self, response):
        print(f"Status Code: {response.status_code}")
        try:
            data = response.json()
            print("JSON Response:")
            print(json.dumps(data, indent=4))
        except json.JSONDecodeError:
            print("Response is not JSON.")
            print("First 200 chars:", response.text[:200])

def main():
    print("=== Surf Lamp API Tester ===")
    default_url = "http://127.0.0.1:5001"
    url = input(f"Enter server URL (default: {default_url}): ").strip() or default_url
    
    client = SurfLampClient(url)

    while True:
        print("\n--- Menu ---")
        print("1. Login")
        print("2. Get Arduino Data (Public Endpoint)")
        print("3. Update Location (Requires Login)")
        print("4. Get Chat Status (Requires Login)")
        print("5. Exit")
        
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            email = input("Email: ")
            password = getpass.getpass("Password: ")
            client.login(email, password)
        elif choice == '2':
            aid = input("Enter Arduino ID (e.g. 12345): ")
            client.get_arduino_data(aid)
        elif choice == '3':
            loc = input("Enter new location (e.g. 'Tel Aviv, Israel'): ")
            client.update_location(loc)
        elif choice == '4':
            client.get_chat_status()
        elif choice == '5':
            print("Exiting.")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
