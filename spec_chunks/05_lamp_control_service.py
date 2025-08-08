Create file: app/business_logic/services/lamp_control_service.py

Implement ILampControlService interface from shared.contracts:
- Import all required interfaces (ILampRepository, ICacheManager, ISurfDataProvider, etc.)
- Implement get_lamp_configuration_data(lamp_id: str) -> ArduinoResponse
- Business logic flow:
  1. Validate lamp_id using IInputValidator
  2. Get lamp config from ILampRepository
  3. Check cache for surf data using ICacheManager
  4. Fetch fresh data from ISurfDataProvider if cache miss
  5. Format complete ArduinoResponse
  6. Log activity using IActivityLogger
- Implement process_user_registration(registration_data) -> Dict
- Include comprehensive error handling
- Use async/await for all operations
- Add structured logging