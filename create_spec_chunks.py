#!/usr/bin/env python3
"""
Script to create all 19 specification chunk files for the multi-agent system
"""
import os

def create_all_spec_chunks():
    """Create all specification chunk files"""
    
    # Create spec_chunks directory
    os.makedirs("spec_chunks", exist_ok=True)
    
    chunks = {
        "01_directory_structure.txt": """Create the complete directory structure for the surfboard-lamp-backend project:

surfboard-lamp-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py  
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── lamps.py
│   │           ├── users.py
│   │           └── health.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── surf_lamp_agent.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── arduino_communication.py
│   │       ├── api_data_retrieval.py
│   │       ├── database_management.py
│   │       └── user_input_processing.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── cache.py
│   │   └── scheduler.py
│   └── db/
│       ├── __init__.py
│       └── models.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt
└── Dockerfile""",

        "02_database_schema.sql.txt": """Create file: app/db/schema.sql

Complete PostgreSQL database schema for the surfboard lamp backend:

-- Lamp Registry Table
CREATE TABLE lamp_registry (
    lamp_id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    location_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- API Configuration Table  
CREATE TABLE api_configuration (
    id SERIAL PRIMARY KEY,
    website_name VARCHAR(100) NOT NULL,
    full_url VARCHAR(500) NOT NULL,
    is_json BOOLEAN NOT NULL DEFAULT true,
    is_metric BOOLEAN NOT NULL DEFAULT true,
    api_key VARCHAR(255),
    city JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- System Configuration Table
CREATE TABLE system_configuration (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activity Log Table
CREATE TABLE activity_log (
    id SERIAL PRIMARY KEY,
    lamp_id UUID REFERENCES lamp_registry(lamp_id),
    activity_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_lamp_registry_email ON lamp_registry(email);
CREATE INDEX idx_lamp_registry_location ON lamp_registry(location_index);
CREATE INDEX idx_activity_log_lamp_time ON activity_log(lamp_id, created_at);""",

        "03_fastapi_main.py.txt": """Create file: app/main.py

FastAPI main application entry point that:
- Sets up FastAPI app with title "Surfboard Lamp Backend"
- Includes CORS middleware
- Sets up lifespan context for startup/shutdown
- Includes v1 API router with prefix "/api/v1"
- Has health check endpoint at "/health"
- Initializes database connection on startup
- Starts background scheduler for surf data updates
- Includes structured logging setup
- Has graceful shutdown handling""",

        "04_endpoint_lamps.py.txt": """Create file: app/api/v1/endpoints/lamps.py

Handle Arduino device requests:
- Implement GET /api/v1/lamps/{lamp_id}/config endpoint
- Use ArduinoCommunicationTool to fetch lamp configuration and surf data
- Return exact JSON format expected by Arduino:
{
    "registered": bool,
    "brightness": int,
    "location_used": str,
    "wave_height_m": float | None,
    "wave_period_s": float | None,
    "wind_speed_mps": float | None,
    "wind_deg": int | None,
    "error": str | None
}""",

        "05_endpoint_users.py.txt": """Create file: app/api/v1/endpoints/users.py

Handle user registration from web interface:
- Implement POST /api/v1/register endpoint
- Accept user registration data (name, email, password, lamp_id, location)
- Use UserInputProcessingTool to validate and process data
- Return success or error message
- Include proper HTTP status codes""",

        "06_endpoint_health.py.txt": """Create file: app/api/v1/endpoints/health.py

Provide monitoring endpoints:
- GET /health - simple "healthy" status response
- GET /ready - check database connection for readiness
- Include proper error handling for database check failures
- Return appropriate HTTP status codes""",

        "07_langchain_agent.py.txt": """Create file: app/agents/surf_lamp_agent.py

Main LangChain agent class:
- Create SurfLampAgent class
- Initialize all four tools (ArduinoCommunicationTool, APIDataRetrievalTool, DatabaseManagementTool, UserInputProcessingTool)
- Primary method: get_lamp_configuration(lamp_id)
- Use tools in sequence to fetch data and format response
- Include comprehensive error handling""",

        "08_tool_arduino_communication.py.txt": """Create file: app/agents/tools/arduino_communication.py

Arduino HTTP communication tool:
- Create ArduinoCommunicationTool class
- Main method: handle_lamp_config_request(lamp_id)
- Helper methods for different response states:
  - _create_unregistered_response()
  - _create_data_error_response()
  - _create_server_error_response()
- Format responses exactly as Arduino expects
- Include activity logging""",

        "09_tool_api_data_retrieval.py.txt": """Create file: app/agents/tools/api_data_retrieval.py

External surf API integration:
- Create APIDataRetrievalTool class
- Main method: fetch_surf_data(website_url, api_key, location_data)
- Handle HTTP requests with proper headers and authentication
- Include robust error handling (timeouts, status codes)
- Method: _standardize_surf_data() to convert different API responses
- Support both paid and free API providers""",

        "10_tool_database_management.py.txt": """Create file: app/agents/tools/database_management.py

Database operations tool:
- Create DatabaseManagementTool class
- Methods: get_lamp_configuration(lamp_id), register_new_user(user_data)
- Additional methods: get_all_active_lamps(), get_lamp_status()
- Use async database connection pool
- Include proper transaction handling
- Add comprehensive error logging""",

        "11_tool_user_input_processing.py.txt": """Create file: app/agents/tools/user_input_processing.py

User registration processing:
- Create UserInputProcessingTool class
- Main method: process_registration(registration_data)
- Validate input data (email format, password strength)
- Use PasswordHasher for secure password hashing
- Convert location names to indices
- Delegate database operations to DatabaseManagementTool""",

        "12_db_models.py.txt": """Create file: app/db/models.py

SQLAlchemy ORM models:
- Define LampRegistry model mapping to lamp_registry table
- Define APIConfiguration model mapping to api_configuration table
- Define SystemConfiguration and ActivityLog models
- Include all columns with correct data types (UUID, String, Integer, JSONB)
- Set up relationships and constraints
- Add __repr__ methods for debugging""",

        "13_core_database.py.txt": """Create file: app/core/database.py

Database connection management:
- Initialize asyncpg connection pool using settings.database_url
- Define get_db_pool() FastAPI dependency function
- Include database initialization logic
- Add connection pool configuration (size, max connections)
- Handle database connection errors gracefully""",

        "14_core_cache.py.txt": """Create file: app/core/cache.py

Redis caching for surf data:
- Create CacheManager class using redis async client
- Methods: get_surf_data_cache(location_index), set_surf_data_cache(location_index, data)
- Set TTL of 30 minutes (1800 seconds) for cached data
- Include cache key formatting and JSON serialization
- Add cache miss/hit logging""",

        "15_core_scheduler.py.txt": """Create file: app/core/scheduler.py

Background task scheduler:
- Create SurfDataScheduler class using apscheduler
- Job that runs every 30 minutes: _update_cache_for_all_locations
- Use DatabaseManagementTool to get active locations
- Use APIDataRetrievalTool to fetch fresh surf data
- Update cache via CacheManager
- Include comprehensive error handling""",

        "16_config_config.py.txt": """Create file: app/config.py

Application configuration:
- Create Settings class using pydantic_settings.BaseSettings
- Define all configuration variables:
  - database_url, database_pool_size
  - surfline_api_key, weather_api_key
  - secret_key, log_level
  - surf_update_interval_minutes
- Load values from .env file
- Include validation and defaults""",

        "17_requirements.txt.txt": """Create file: requirements.txt

Complete Python dependencies list:
fastapi==0.104.1
langchain==0.0.350
uvicorn==0.24.0
boto3==1.34.0
paho-mqtt==1.6.1
asyncpg==0.29.0
sqlalchemy==2.0.23
alembic==1.13.1
httpx==0.25.2
pydantic==2.5.0
python-multipart==0.0.6
structlog==23.2.0
prometheus-client==0.19.0
pydantic-settings==2.1.0
apscheduler==3.10.4
redis==5.0.1
bcrypt==4.1.2
python-dotenv==1.0.0""",

        "18_Dockerfile.txt": """Create file: Dockerfile

Multi-stage Docker build:
- Use python:3.11-slim base image
- Install system dependencies (gcc for compilation)
- Copy and install requirements.txt
- Copy application code
- Create non-root user for security
- Expose port 8000
- Add HEALTHCHECK instruction
- Set CMD to run uvicorn app.main:app""",

        "19_docker-compose.yml.txt": """Create file: docker-compose.yml

Multi-container development environment:
- backend service: build from Dockerfile, port 8000
- db service: postgres:15 image, port 5432
- redis service: redis:7-alpine image, port 6379
- Configure environment variables
- Set up networks for inter-service communication
- Include volume mounts for database persistence
- Add depends_on relationships"""
    }
    
    print("🌊 Creating Multi-Agent Specification Chunks")
    print("=" * 50)
    
    # Write all chunk files
    for filename, content in chunks.items():
        filepath = os.path.join("spec_chunks", filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {filename}")
    
    print(f"\n🎉 Successfully created {len(chunks)} specification chunks!")
    print(f"📁 All chunks saved in: spec_chunks/")
    print("\n🚀 Ready for multi-agent code generation!")
    
    return len(chunks)

if __name__ == "__main__":
    chunk_count = create_all_spec_chunks()
    print(f"\n📊 Summary: {chunk_count} chunks ready for processing")
