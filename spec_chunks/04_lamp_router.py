Create file: app/api/routers/lamp_router.py

Arduino lamp configuration endpoint implementation:
- Import interfaces from shared.contracts (ILampControlService, ArduinoResponse)
- Create FastAPI router for lamp endpoints
- Implement GET /api/v1/lamps/{lamp_id}/config endpoint
- Use dependency injection for ILampControlService
- Return ArduinoResponse format exactly:
{
    "registered": bool,
    "brightness": int,
    "location_used": str,
    "wave_height_m": float | None,
    "wave_period_s": float | None,
    "wind_speed_mps": float | None,
    "wind_deg": int | None,
    "error": str | None
}
- Include proper error handling for LampNotFoundError, ValidationError
- Add structured logging for all requests