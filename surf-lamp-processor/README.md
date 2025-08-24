# Surf Lamp Processor

This directory contains the core logic for the Surf Lamp project. It includes scripts for fetching data from various surf APIs, processing that data, and sending it to the Arduino devices.

## Files

- **`set_arduino_ip.py`**: An interactive script to update an Arduino's IP address in the database.
- **`background_processor.py`**: The main background service that fetches surf data from various APIs, processes it, and sends it to the Arduino devices. It also handles failure tracking and retries.
- **`arduino_transport.py`**: Provides a transport layer for communicating with the Arduino, with support for both real HTTP requests and a mock transport for development.
- **`background_processor_backup.py`**: A backup of the background processor.
- **`endpoint_configs.py`**: Contains the configurations and field mappings for the different surf data API endpoints.
- **`test_background_processor.py`**: A test runner for the background processor.
- **`thread_safe_background_processor.py`**: A thread-safe version of the background processor, optimized for parallel processing of Arduino updates.