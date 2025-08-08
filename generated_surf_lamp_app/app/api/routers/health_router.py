```
from fastapi import APIRouter, Depends, HTTPException
from shared.contracts import ILampControlService, IInputValidator

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "healthy"}

@router.get("/ready")
async def ready(
    lamp_service: ILampControlService = Depends(),
    validator: IInputValidator = Depends()
):
    try:
        await lamp_service.get_status()
        validator.validate("test")
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```