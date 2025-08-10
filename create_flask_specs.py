#!/usr/bin/env python3
"""
Create individual spec chunk files for the Database-First Flask approach
"""
import os

def create_spec_chunks():
    """Create specification chunks for Database-First Flask architecture"""
    
    os.makedirs("spec_chunks", exist_ok=True)
    
    chunks = {
        "01_database_foundation.txt": """Create files: 
- database/models.py (SQLAlchemy models)
- database/schema.sql (PostgreSQL schema)  
- contracts/tools_contract.py (Tools interface contract)

GENERATE ONLY PYTHON/SQL CODE for these exact database tables:

1. users table: user_id (PK, AUTO_INCREMENT), username (VARCHAR(255) UNIQUE), password_hash (TEXT), email (VARCHAR(255) UNIQUE), location (VARCHAR(255)), theme (VARCHAR(50)), preferred_output (VARCHAR(50))

2. lamps table: lamp_id (PK), user_id (FK to users), arduino_id (INTEGER UNIQUE), arduino_ip (VARCHAR(15)), last_updated (TIMESTAMP)

3. daily_usage table: usage_id (PK, AUTO_INCREMENT), website_url (VARCHAR(255) UNIQUE), last_updated (TIMESTAMP)

4. location_websites table: location (VARCHAR(255) PK), usage_id (FK to daily_usage, UNIQUE)

5. usage_lamps table: usage_id (FK to daily_usage), lamp_id (FK to lamps), api_key (TEXT), http_endpoint (TEXT) - Composite PK (usage_id, lamp_id)

Create SQLAlchemy models with proper relationships and a tools contract defining:
- get_all_lamp_ids() -> List[int]
- get_lamp_details(lamp_id: int) -> dict with arduino_id and websites list
- fetch_website_data(api_key: str, endpoint: str) -> dict  
- send_to_arduino(arduino_id: int, data: dict, output_format: str) -> bool
- update_lamp_timestamp(lamp_id: int) -> bool

Use psycopg2 and SQLAlchemy. Create proper foreign key relationships.""",

        "02_agent_tools.txt": """Create file: tools/agent_tools.py

GENERATE ONLY PYTHON CODE implementing the 5 agent tools from contracts/tools_contract.py:

Import the database models and implement these functions:

1. get_all_lamp_ids() -> List[int]
   Query lamps table for all lamp_ids, return list of integers

2. get_lamp_details(lamp_id: int) -> dict
   Join lamps with usage_lamps and daily_usage tables
   Return: {'arduino_id': int, 'arduino_ip': str, 'websites': [{'url': str, 'api_key': str, 'endpoint': str}]}

3. fetch_website_data(api_key: str, endpoint: str) -> dict
   Make HTTP GET request to endpoint with api_key
   Return surf condition data: {
     "wave_height_m": float,
     "wave_period_s": float,
     "wind_speed_mps": float, 
     "wind_deg": int,
     "location": str,
     "timestamp": int
   }

4. send_to_arduino(arduino_id: int, data: dict, output_format: str) -> bool
   HTTP POST formatted surf data to Arduino's local IP address
   Look up Arduino IP address from arduino_id in database
   POST to http://{arduino_ip}/api/update with JSON payload:
   {
     "wave_height_m": float,
     "wave_period_s": float, 
     "wind_speed_mps": float,
     "wind_deg": int,
     "location": str,
     "timestamp": int
   }
   Return True/False for success/failure

5. update_lamp_timestamp(lamp_id: int) -> bool
   Update last_updated timestamp for given lamp_id
   Return True/False for success/failure

Use requests library for HTTP calls, SQLAlchemy for database queries.
Include proper error handling and logging.
Must work with Flask (synchronous, not async).""",

        "03_flask_app.txt": """Create file: app.py

GENERATE ONLY PYTHON CODE for Flask application:

Import tools from tools/agent_tools.py and create these routes:

1. GET /api/lamp/config?id={lamp_id}
   Arduino registration/configuration endpoint  
   Return JSON: {
     "registered": bool,
     "lamp_id": int,
     "update_interval": int,  
     "status": str,
     "error": str or null
   }
   Used for Arduino to confirm registration and get configuration settings

2. POST /api/register  
   User registration endpoint
   Accept: {username, email, password, location, lamp_id, arduino_id, arduino_ip}
   Use flask_bcrypt for password hashing

3. GET /health
   Health check endpoint returning {"status": "ok"}

4. Background processing function that:
   - Calls get_all_lamp_ids()
   - For each lamp: get_lamp_details(), fetch_website_data(), send_to_arduino(), update_lamp_timestamp()

Use Flask, flask_bcrypt, python-dotenv for configuration.
Include proper error handling, logging, CORS headers.""",

        "04_config_setup.txt": """Create files:
- requirements.txt
- config.py
- logging_config.py
- .env.example

GENERATE ONLY the file contents:

requirements.txt should contain:
Flask==2.3.3
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
flask-bcrypt==1.0.1
requests==2.31.0
python-dotenv==1.0.0

config.py should contain:
Database connection settings, API key management, Flask configuration.
Use environment variables for all sensitive data.

logging_config.py should contain:
Python logging configuration with formatters, handlers for console and file output.
Different log levels for development vs production.
Structured logging format for easy parsing.

.env.example should contain:
DATABASE_URL=postgresql://user:password@localhost/surfboard_lamp
SURFLINE_API_KEY=your_surfline_key_here
WEATHER_API_KEY=your_weather_key_here
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development
LOG_LEVEL=INFO
LOG_FILE=surfboard_lamp.log""",

        "05_database_setup.txt": """Create files:
- setup_database.py  
- seed_data.sql

GENERATE ONLY PYTHON/SQL CODE:

setup_database.py should:
- Connect to PostgreSQL using psycopg2
- Create all tables from the schema
- Set up foreign key constraints and indexes
- Handle existing tables gracefully

seed_data.sql should contain:
- INSERT statements for sample locations (San Diego, Santa Cruz, Honolulu, etc.)
- Sample API configurations for Surfline and WeatherAPI
- Sample users and lamps for testing

Include proper foreign key constraints, indexes for performance.
Must work with PostgreSQL and psycopg2.""",

        "06_background_processing.txt": """Create files:
- background/lamp_processor.py
- background/scheduler.py

GENERATE ONLY PYTHON CODE:

lamp_processor.py should contain:
- LampProcessor class that implements the main processing loop
- process_all_lamps() method that calls get_all_lamp_ids() and processes each
- process_single_lamp(lamp_id) method that:
  1. Calls get_lamp_details(lamp_id) to get Arduino IP and websites
  2. For each website: calls fetch_website_data(api_key, endpoint)
  3. Formats surf data and sends via HTTP POST to Arduino IP using send_to_arduino(arduino_id, data, format)
  4. Calls update_lamp_timestamp(lamp_id)
- Error handling for failed API calls, Arduino communication
- Logging for each step of the process

scheduler.py should contain:
- Flask CLI command to run lamp processing manually
- Option for cron job scheduling (30-minute intervals)
- Graceful shutdown handling
- Process status monitoring and health checks

Use the agent tools from tools/agent_tools.py.
Include proper logging using logging_config.py setup."""
    }
    
    print("🌊 Creating Database-First Flask Spec Chunks")
    print("=" * 50)
    
    for filename, content in chunks.items():
        filepath = os.path.join("spec_chunks", filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {filename}")
    
    print(f"\n🎉 Created {len(chunks)} spec chunks!")
    print("\nBuild Order:")
    print("1. Database Specialist (Gemini) → 01_database_foundation.txt")
    print("2. Tools Specialist (Grok) → 02_agent_tools.txt") 
    print("3. Web Specialist (ChatGPT) → 03_flask_app.txt")
    print("4. Infrastructure (ChatGPT) → 04_config_setup.txt")
    print("5. Database Specialist (Gemini) → 05_database_setup.txt")
    print("6. Background Processing (Grok) → 06_background_processing.txt")

if __name__ == "__main__":
    create_spec_chunks()
