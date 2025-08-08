```
from shared.contracts import ILampControlService, IInputValidator
from lamp_control.domain import LampControlService
from input_validation.domain import InputValidator
from database import create_connection_pool

async def get_lamp_service() -> ILampControlService:
    try:
        lamp_service = LampControlService()
        await lamp_service.initialize()
        return lamp_service
    except Exception as e:
        raise RuntimeError("Failed to initialize lamp service") from e

async def get_input_validator() -> IInputValidator:
    try:
        validator = InputValidator()
        await validator.initialize()
        return validator
    except Exception as e:
        raise RuntimeError("Failed to initialize input validator") from e

async def get_database_pool():
    try:
        pool = await create_connection_pool()
        return pool
    except Exception as e:
        raise RuntimeError("Failed to create database connection pool") from e
```