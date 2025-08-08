"""
Surfboard Lamp Backend - Immutable Interface Contracts
=========================================================

This file defines ALL interfaces that domains must implement.
NO LLM is allowed to modify these definitions.
ALL cross-domain communication MUST use these interfaces.

Generated: 2025-08-07
Version: 2.0+
Status: IMMUTABLE - DO NOT MODIFY
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# CRITICAL: Arduino Communication Interface
# ============================================================================

class ArduinoResponse(Dict[str, Any]):
    """
    IMMUTABLE: Arduino expects EXACTLY this JSON format.
    Any deviation will break hardware communication.
    """
    def __init__(self):
        super().__init__({
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None, 
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": None
        })


class IArduinoCommunication(ABC):
    """Arduino HTTP endpoint communication interface"""
    
    @abstractmethod
    async def handle_lamp_config_request(self, lamp_id: str) -> ArduinoResponse:
        """
        CRITICAL: Return Arduino-compatible response for lamp configuration
        
        Args:
            lamp_id: Unique lamp identifier
            
        Returns:
            ArduinoResponse: Exact format expected by Arduino firmware
        """
        pass


# ============================================================================
# Database Layer Interfaces
# ============================================================================

class LampConfig(Dict[str, Any]):
    """Standard lamp configuration structure"""
    pass


class ILampRepository(ABC):
    """Database operations for lamp registry"""
    
    @abstractmethod
    async def get_lamp_configuration(self, lamp_id: str) -> Optional[LampConfig]:
        """Retrieve lamp configuration by ID"""
        pass
    
    @abstractmethod
    async def register_new_lamp(self, lamp_data: Dict[str, Any]) -> bool:
        """Register new lamp in database"""
        pass
    
    @abstractmethod
    async def get_all_active_lamps(self) -> List[LampConfig]:
        """Get all currently active lamps"""
        pass
    
    @abstractmethod
    async def update_lamp_status(self, lamp_id: str, status: str) -> bool:
        """Update lamp status"""
        pass


class IUserRepository(ABC):
    """Database operations for user management"""
    
    @abstractmethod
    async def register_user(self, user_data: Dict[str, Any]) -> bool:
        """Register new user"""
        pass
    
    @abstractmethod
    async def validate_user_credentials(self, email: str, password_hash: str) -> bool:
        """Validate user login"""
        pass


class IActivityLogger(ABC):
    """Activity logging interface"""
    
    @abstractmethod
    async def log_activity(self, lamp_id: str, activity_type: str, 
                          status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log lamp activity"""
        pass


# ============================================================================
# External API Integration Interfaces
# ============================================================================

class SurfData(Dict[str, Any]):
    """Standardized surf data structure"""
    def __init__(self):
        super().__init__({
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "location_name": "",
            "timestamp": None,
            "data_source": ""
        })


class ISurfDataProvider(ABC):
    """External surf API data retrieval"""
    
    @abstractmethod
    async def fetch_surf_data(self, location_index: int) -> Optional[SurfData]:
        """
        Fetch surf data for location
        
        Args:
            location_index: Numeric location identifier
            
        Returns:
            SurfData: Standardized surf conditions or None if failed
        """
        pass
    
    @abstractmethod
    async def validate_api_keys(self) -> Dict[str, bool]:
        """Check if API keys are valid"""
        pass


# ============================================================================
# Caching Layer Interfaces  
# ============================================================================

class ICacheManager(ABC):
    """Surf data caching interface"""
    
    @abstractmethod
    async def get_surf_data_cache(self, location_index: int) -> Optional[SurfData]:
        """Retrieve cached surf data"""
        pass
    
    @abstractmethod
    async def set_surf_data_cache(self, location_index: int, data: SurfData, 
                                 ttl_seconds: int = 1800) -> None:
        """Cache surf data with TTL"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, location_index: int) -> None:
        """Remove cached data for location"""
        pass


# ============================================================================
# Business Logic Interfaces
# ============================================================================

class ILampControlService(ABC):
    """Core lamp business logic"""
    
    @abstractmethod
    async def get_lamp_configuration_data(self, lamp_id: str) -> ArduinoResponse:
        """
        Main business logic for lamp configuration requests
        Orchestrates data fetching, caching, and response formatting
        """
        pass
    
    @abstractmethod
    async def process_user_registration(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process new user registration with validation"""
        pass


class IBackgroundScheduler(ABC):
    """Background task scheduling"""
    
    @abstractmethod
    async def start_surf_data_updates(self) -> None:
        """Start periodic surf data refresh (30-minute cycle)"""
        pass
    
    @abstractmethod
    async def stop_scheduler(self) -> None:
        """Gracefully stop background tasks"""
        pass


# ============================================================================
# Security & Validation Interfaces
# ============================================================================

class IPasswordSecurity(ABC):
    """Password hashing and validation"""
    
    @abstractmethod
    async def hash_password(self, password: str) -> str:
        """Hash password securely"""
        pass
    
    @abstractmethod
    async def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        pass


class IInputValidator(ABC):
    """Input validation services"""
    
    @abstractmethod
    async def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pass
    
    @abstractmethod
    async def validate_lamp_id(self, lamp_id: str) -> bool:
        """Validate lamp ID format"""
        pass
    
    @abstractmethod
    async def validate_location_index(self, location_index: int) -> bool:
        """Validate location index is supported"""
        pass


# ============================================================================
# Error Types
# ============================================================================

class SurfLampError(Exception):
    """Base exception for surf lamp system"""
    pass


class LampNotFoundError(SurfLampError):
    """Lamp ID not found in database"""
    pass


class DataUnavailableError(SurfLampError):
    """Surf data temporarily unavailable"""
    pass


class ValidationError(SurfLampError):
    """Input validation failed"""
    pass


class DatabaseError(SurfLampError):
    """Database operation failed"""
    pass


# ============================================================================
# Configuration Types
# ============================================================================

class LocationIndex(Enum):
    """Supported surf locations"""
    SAN_DIEGO = 0
    SANTA_CRUZ = 1
    HONOLULU = 2
    HUNTINGTON_BEACH = 3
    MALIBU = 4


# ============================================================================
# Contract Validation
# ============================================================================

def validate_arduino_response(response: Dict[str, Any]) -> bool:
    """
    Validate response matches Arduino expectations exactly
    
    Critical: Arduino firmware depends on this exact structure
    """
    required_keys = {
        "registered", "brightness", "location_used", 
        "wave_height_m", "wave_period_s", "wind_speed_mps", 
        "wind_deg", "error"
    }
    
    if not isinstance(response, dict):
        return False
        
    if set(response.keys()) != required_keys:
        return False
        
    # Type validation
    if not isinstance(response["registered"], bool):
        return False
    if not isinstance(response["brightness"], int):
        return False
    if not isinstance(response["location_used"], str):
        return False
        
    # Optional fields can be None
    for key in ["wave_height_m", "wave_period_s", "wind_speed_mps", "wind_deg"]:
        if response[key] is not None:
            if key == "wind_deg" and not isinstance(response[key], int):
                return False
            elif key != "wind_deg" and not isinstance(response[key], (int, float)):
                return False
    
    if response["error"] is not None and not isinstance(response["error"], str):
        return False
        
    return True


# ============================================================================
# CONTRACT ENFORCEMENT
# ============================================================================

__all__ = [
    # Arduino Interface
    'IArduinoCommunication', 'ArduinoResponse',
    
    # Database Interfaces  
    'ILampRepository', 'IUserRepository', 'IActivityLogger',
    'LampConfig',
    
    # External API Interfaces
    'ISurfDataProvider', 'SurfData',
    
    # Caching Interfaces
    'ICacheManager',
    
    # Business Logic Interfaces
    'ILampControlService', 'IBackgroundScheduler',
    
    # Security Interfaces
    'IPasswordSecurity', 'IInputValidator',
    
    # Error Types
    'SurfLampError', 'LampNotFoundError', 'DataUnavailableError',
    'ValidationError', 'DatabaseError',
    
    # Configuration
    'LocationIndex',
    
    # Validation
    'validate_arduino_response'
]

"""
CONTRACT RULES:
===============

1. NO LLM MAY MODIFY THIS FILE
2. ALL imports between domains MUST use these interfaces
3. ALL method signatures are IMMUTABLE
4. Arduino response format is SACRED - validate_arduino_response() enforces this
5. New features require NEW interfaces, not modifications
6. Each domain implements ONLY its assigned interfaces
7. Cross-domain communication ONLY through these contracts

VIOLATION OF THESE RULES WILL BREAK THE ENTIRE SYSTEM
"""
