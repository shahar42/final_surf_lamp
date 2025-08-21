# surf-lamp-processor - Component Overview

## Purpose & Role
- **What this component does**: This component is the core of the surf lamp system. It runs in the background, fetches surf data, processes it, and sends it to the Arduino-based hardware to control the lamp.
- **Position in overall architecture**: This is the main backend processing component.
- **Primary responsibility**: To orchestrate the flow of data from the web and database component to the physical lamp hardware.

## Key Files & Functions
### Critical Files
- `background_processor.py` - The main script that runs the background processing loop.
- `arduino_transport.py` - Handles sending data to the Arduino hardware via HTTP POST requests.
- `endpoint_configs.py` - Configuration for the API endpoints to fetch data from the web and database component.
- `thread_safe_background_processor.py` - A thread-safe version of the background processor.
- `test_background_processor.py` - Unit tests for the background processor.
- `requirements.txt` - Python dependencies for this component.
- `runtime.txt` - Specifies the Python runtime version.

### Entry Points
- **Main execution**: The `background_processor.py` or `thread_safe_background_processor.py` script is the primary entry point.
- **API endpoints**: This component does not expose any API endpoints.
- **External interfaces**: This component interacts with the `web_and_database` component to fetch data and with the Arduino hardware to send data over the network.

## Data Flow
### Inputs
- **Receives from**: The `web_and_database` component.
- **Input format**: JSON data from the API endpoints defined in `endpoint_configs.py`.
- **Trigger conditions**: The background processor runs continuously and fetches data at regular intervals.

### Outputs
- **Sends to**: The network-aware Arduino hardware.
- **Output format**: JSON data sent via an HTTP POST request to the Arduino's `/api/update` endpoint.
- **Side effects**: This component may log information to the console or a log file.

## Dependencies & Configuration
### External Dependencies
- **Database**: This component does not directly connect to a database, but it relies on the `web_and_database` component to provide data from the database.
- **APIs**: This component calls the API endpoints exposed by the `web_and_database` component.
- **Network**: Requires network access to communicate with the `web_and_database` component and the Arduino hardware.

### Environment Variables
```bash
# The transport method to the Arduino is controlled by an environment variable.
# ARDUINO_TRANSPORT: 'http' (default) for real requests, or 'mock' for simulated logging.
```
