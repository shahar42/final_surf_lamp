#!/usr/bin/env python3
"""
Script to create specification chunks that explicitly demand code generation
"""
import os

def create_all_spec_chunks():
    """Create specification chunks that force code generation"""
    
    # Create spec_chunks directory
    os.makedirs("spec_chunks", exist_ok=True)
    
    chunks = {
        "01_directory_structure.txt": """Create the complete directory structure for the surfboard-lamp-backend project:

surfboard-lamp-backend/
├── shared/
│   └── contracts.py
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── middleware.py
│   │   ├── models.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── lamp_router.py
│   │       ├── user_router.py
│   │       └── health_router.py
│   ├── business_logic/
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── lamp_control_service.py
│   │   │   └── background_scheduler.py
│   │   └── agents/
│   │       ├── __init__.py
│   │       └── surf_lamp_agent.py
│   ├── data_layer/
│   │   ├── __init__.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── lamp_repository.py
│   │   │   ├── user_repository.py
│   │   │   └── activity_logger.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── cache_manager.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── database_models.py
│   │   └── connection/
│   │       ├── __init__.py
│   │       └── database_manager.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── external/
│       │   ├── __init__.py
│       │   └── surf_data_provider.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── password_security.py
│       │   └── input_validator.py
│       └── config/
│           ├── __init__.py
│           └── settings.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml""",

        "02_fastapi_main.py.txt": """Create file: app/main.py

GENERATE ONLY THIS PYTHON CODE:

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import routers - these will be created by other chunks
from app.api.routers import lamp_router, user_router, health_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Surfboard Lamp Backend")
    yield
    # Shutdown
    logger.info("Shutting down Surfboard Lamp Backend")

app = FastAPI(
    title="Surfboard Lamp Backend",
    description="Backend API for surf data delivery to IoT lamps",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lamp_router.router, prefix="/api/v1/lamps", tags=["lamps"])
app.include_router(user_router.router, prefix="/api/v1", tags=["users"])
app.include_router(health_router.router, tags=["health"])

@app.get("/")
async def root():
    return {"message": "Surfboard Lamp Backend API", "version": "1.0.0"}""",

        "03_lamp_router.py.txt": """Create file: app/api/routers/lamp_router.py

GENERATE ONLY PYTHON CODE for Arduino endpoint that returns EXACT format:

from fastapi import APIRouter, Depends, HTTPException
from shared.contracts import ILampControlService, ArduinoResponse, LampNotFoundError, ValidationError, validate_arduino_response
from app.dependencies import get_lamp_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{lamp_id}/config", response_model=dict)
async def get_lamp_config(
    lamp_id: str,
    lamp_service: ILampControlService = Depends(get_lamp_service)
):
    '''Get lamp configuration for Arduino device - MUST return exact Arduino format'''
    try:
        logger.info(f"Lamp config request for: {lamp_id}")
        
        # Get configuration from service
        response = await lamp_service.get_lamp_configuration_data(lamp_id)
        
        # Validate response format
        if not validate_arduino_response(response):
            logger.error("Invalid Arduino response format")
            raise HTTPException(status_code=500, detail="Response format error")
        
        return response
        
    except LampNotFoundError:
        logger.warning(f"Lamp not found: {lamp_id}")
        raise HTTPException(status_code=404, detail="Lamp not found")
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")""",

        "04_user_router.py.txt": """Create file: app/api/routers/user_router.py

GENERATE ONLY PYTHON CODE for user registration:

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from shared.contracts import ILampControlService, IInputValidator, ValidationError
from app.dependencies import get_lamp_service, get_input_validator
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class UserRegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    lamp_id: str = Field(min_length=3, max_length=50)
    location_index: int = Field(ge=0, le=4)

class UserRegistrationResponse(BaseModel):
    success: bool
    message: str
    errors: Optional[List[str]] = None

@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    lamp_service: ILampControlService = Depends(get_lamp_service),
    validator: IInputValidator = Depends(get_input_validator)
):
    '''Register new user and lamp'''
    try:
        # Validate inputs
        is_valid_email = await validator.validate_email(request.email)
        is_valid_lamp = await validator.validate_lamp_id(request.lamp_id)
        is_valid_location = await validator.validate_location_index(request.location_index)
        
        if not all([is_valid_email, is_valid_lamp, is_valid_location]):
            return UserRegistrationResponse(
                success=False,
                message="Validation failed",
                errors=["Invalid input data"]
            )
        
        # Process registration
        result = await lamp_service.process_user_registration(request.dict())
        
        return UserRegistrationResponse(
            success=result.get("success", False),
            message=result.get("message", "Registration processed"),
            errors=result.get("errors")
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")""",

        "05_health_router.py.txt": """Create file: app/api/routers/health_router.py

GENERATE ONLY PYTHON CODE for health checks:

from fastapi import APIRouter, Depends, HTTPException
from shared.contracts import ILampControlService, IInputValidator
from app.dependencies import get_lamp_service, get_input_validator
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: Optional[str] = None

@router.get("/health", response_model=HealthCheckResponse)
async def health():
    '''Simple health check'''
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/ready", response_model=HealthCheckResponse)
async def ready(
    lamp_service: ILampControlService = Depends(get_lamp_service),
    validator: IInputValidator = Depends(get_input_validator)
):
    '''Readiness check with dependency validation'''
    try:
        # Test that services can be injected
        if lamp_service is None or validator is None:
            raise HTTPException(status_code=503, detail="Services not ready")
        
        return HealthCheckResponse(
            status="ready",
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")""",

        "06_lamp_control_service.py.txt": """Create file: app/business_logic/services/lamp_control_service.py

GENERATE PYTHON CODE implementing ILampControlService from shared.contracts:

from shared.contracts import (
    ILampControlService, ILampRepository, ISurfDataProvider, 
    ICacheManager, IActivityLogger, IPasswordSecurity, IInputValidator,
    ArduinoResponse, LampConfig, SurfData,
    LampNotFoundError, ValidationError
)
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

class LampControlService(ILampControlService):
    def __init__(
        self,
        lamp_repo: ILampRepository,
        surf_provider: ISurfDataProvider,
        cache_manager: ICacheManager,
        activity_logger: IActivityLogger,
        password_security: IPasswordSecurity,
        validator: IInputValidator
    ):
        self.lamp_repo = lamp_repo
        self.surf_provider = surf_provider
        self.cache_manager = cache_manager
        self.activity_logger = activity_logger
        self.password_security = password_security
        self.validator = validator

    async def get_lamp_configuration_data(self, lamp_id: str) -> ArduinoResponse:
        '''Get lamp config and surf data, return Arduino format'''
        try:
            # Validate lamp_id
            if not await self.validator.validate_lamp_id(lamp_id):
                raise ValidationError(f"Invalid lamp ID: {lamp_id}")
            
            # Get lamp configuration
            lamp_config = await self.lamp_repo.get_lamp_configuration(lamp_id)
            
            if not lamp_config:
                # Return unregistered response
                response = ArduinoResponse()
                response.update({
                    "registered": False,
                    "brightness": 50,
                    "location_used": "",
                    "wave_height_m": None,
                    "wave_period_s": None,
                    "wind_speed_mps": None,
                    "wind_deg": None,
                    "error": "Lamp not registered. Visit setup portal."
                })
                await self.activity_logger.log_activity(
                    lamp_id, "config_request", "unregistered", None
                )
                return response
            
            # Get surf data
            location_index = lamp_config.get("location_index", 0)
            surf_data = await self._get_surf_data_with_cache(location_index)
            
            # Create response
            response = ArduinoResponse()
            response.update({
                "registered": True,
                "brightness": lamp_config.get("brightness", 100),
                "location_used": lamp_config.get("location_name", ""),
                "wave_height_m": surf_data.get("wave_height_m") if surf_data else None,
                "wave_period_s": surf_data.get("wave_period_s") if surf_data else None,
                "wind_speed_mps": surf_data.get("wind_speed_mps") if surf_data else None,
                "wind_deg": surf_data.get("wind_deg") if surf_data else None,
                "error": None if surf_data else "Surf data temporarily unavailable"
            })
            
            await self.activity_logger.log_activity(
                lamp_id, "config_request", "success", 
                {"location": lamp_config.get("location_name")}
            )
            
            return response
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting lamp config: {e}")
            response = ArduinoResponse()
            response["error"] = "System error occurred"
            return response
    
    async def _get_surf_data_with_cache(self, location_index: int) -> Optional[SurfData]:
        '''Get surf data with caching'''
        # Check cache first
        cached_data = await self.cache_manager.get_surf_data_cache(location_index)
        
        if cached_data and self._is_data_fresh(cached_data):
            logger.info(f"Cache hit for location {location_index}")
            return cached_data
        
        # Fetch fresh data
        try:
            fresh_data = await self.surf_provider.fetch_surf_data(location_index)
            if fresh_data:
                await self.cache_manager.set_surf_data_cache(
                    location_index, fresh_data, ttl_seconds=1800
                )
                return fresh_data
        except Exception as e:
            logger.error(f"Failed to fetch fresh data: {e}")
        
        # Return stale cache if available
        return cached_data
    
    def _is_data_fresh(self, data: SurfData, max_age_minutes: int = 30) -> bool:
        '''Check if cached data is fresh'''
        if not data or "timestamp" not in data:
            return False
        age = (time.time() - data["timestamp"]) / 60
        return age < max_age_minutes
    
    async def process_user_registration(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        '''Process user registration'''
        try:
            # Validate all inputs
            is_valid = all([
                await self.validator.validate_email(registration_data.get("email", "")),
                await self.validator.validate_lamp_id(registration_data.get("lamp_id", "")),
                await self.validator.validate_location_index(registration_data.get("location_index", -1))
            ])
            
            if not is_valid:
                return {"success": False, "message": "Validation failed"}
            
            # Hash password
            password_hash = await self.password_security.hash_password(
                registration_data["password"]
            )
            
            # Register lamp
            registration_data["password_hash"] = password_hash
            success = await self.lamp_repo.register_new_lamp(registration_data)
            
            return {
                "success": success,
                "message": "Registration successful" if success else "Registration failed"
            }
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {"success": False, "message": str(e)}""",

        "07_dependencies.py.txt": """Create file: app/dependencies.py

GENERATE ONLY PYTHON CODE for dependency injection:

from shared.contracts import ILampControlService, IInputValidator
from typing import Optional
import os

# Cached instances
_lamp_service: Optional[ILampControlService] = None
_input_validator: Optional[IInputValidator] = None

def get_lamp_service() -> ILampControlService:
    '''Get or create lamp control service'''
    global _lamp_service
    if _lamp_service is None:
        # Import implementations
        from app.business_logic.services.lamp_control_service import LampControlService
        from app.data_layer.repositories.lamp_repository import PostgresLampRepository
        from app.data_layer.cache.cache_manager import RedisCacheManager
        from app.infrastructure.external.surf_data_provider import MultiProviderSurfDataService
        from app.data_layer.repositories.activity_logger import PostgresActivityLogger
        from app.infrastructure.security.password_security import BCryptPasswordSecurity
        from app.infrastructure.security.input_validator import SecurityInputValidator
        
        # Initialize dependencies
        lamp_repo = PostgresLampRepository()
        cache_manager = RedisCacheManager()
        surf_provider = MultiProviderSurfDataService()
        activity_logger = PostgresActivityLogger()
        password_security = BCryptPasswordSecurity()
        validator = SecurityInputValidator()
        
        # Create service
        _lamp_service = LampControlService(
            lamp_repo=lamp_repo,
            surf_provider=surf_provider,
            cache_manager=cache_manager,
            activity_logger=activity_logger,
            password_security=password_security,
            validator=validator
        )
    
    return _lamp_service

def get_input_validator() -> IInputValidator:
    '''Get or create input validator'''
    global _input_validator
    if _input_validator is None:
        from app.infrastructure.security.input_validator import SecurityInputValidator
        _input_validator = SecurityInputValidator()
    return _input_validator

def get_database_url() -> str:
    '''Get database URL from environment'''
    return os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/surflamp")

def get_redis_url() -> str:
    '''Get Redis URL from environment'''
    return os.getenv("REDIS_URL", "redis://localhost:6379")""",

        "08_requirements.txt": """Create file: requirements.txt

GENERATE ONLY THIS CONTENT:
fastapi==0.104.1
uvicorn==0.24.0
asyncpg==0.29.0
sqlalchemy==2.0.23
redis==5.0.1
httpx==0.25.2
pydantic==2.5.0
pydantic-settings==2.1.0
bcrypt==4.1.2
python-multipart==0.0.6
python-dotenv==1.0.0
structlog==23.2.0
apscheduler==3.10.4
langchain==0.0.350
email-validator==2.1.0""",

        "09_Dockerfile.txt": """Create file: Dockerfile

GENERATE ONLY THIS DOCKERFILE CONTENT:
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y gcc && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

RUN useradd -m nonrootuser
USER nonrootuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]""",

        "10_docker-compose.yml.txt": """Create file: docker-compose.yml

GENERATE ONLY THIS DOCKER-COMPOSE CONTENT:
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/surflamp
      - REDIS_URL=redis://redis:6379
      - SURFLINE_API_KEY=${SURFLINE_API_KEY}
      - WEATHER_API_KEY=${WEATHER_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=true
    depends_on:
      - db
      - redis
    volumes:
      - .:/app
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=surflamp
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:"""
    }
    
    print("🌊 Creating Enhanced Specification Chunks")
    print("=" * 50)
    
    # Write all chunk files
    for filename, content in chunks.items():
        filepath = os.path.join("spec_chunks", filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {filename}")
    
    print(f"\n🎉 Successfully created {len(chunks)} specification chunks!")
    print(f"📁 All chunks saved in: spec_chunks/")
    print("\nThese chunks explicitly instruct LLMs to generate ONLY code.")
    
    return len(chunks)

if __name__ == "__main__":
    chunk_count = create_all_spec_chunks()
    print(f"\n📊 Summary: {chunk_count} chunks ready for code generation")
