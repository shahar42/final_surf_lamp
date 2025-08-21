# arduino - Component Overview

## Purpose & Role
- **What this component does**: This directory contains information about the data format for communicating with the Arduino-based surf lamp hardware.
- **Position in overall architecture**: This component represents the hardware interface of the project.
- **Primary responsibility**: To define the data contract between the software components and the physical surf lamp.

## Key Files & Functions
### Critical Files
- `IMPORTANT.txt` - Contains a brief description of the data format for wave height, wave threshold, and wind speed.

### Entry Points
- **Main execution**: N/A
- **API endpoints**: N/A
- **External interfaces**: This component defines the serial communication protocol for the Arduino.

## Data Flow
### Inputs
- **Receives from**: The `surf-lamp-processor` component sends data to the Arduino.
- **Input format**: The data is sent as integers representing wave height (cm), wave threshold (cm), and wind speed.
- **Trigger conditions**: The `surf-lamp-processor` sends data to the Arduino whenever new surf conditions are fetched.

### Outputs
- **Sends to**: The Arduino controls the physical surf lamp hardware.
- **Output format**: The Arduino translates the received data into visual signals on the lamp.
- **Side effects**: The physical state of the surf lamp is changed.

## Dependencies & Configuration
### External Dependencies
- **Hardware**: This component requires an Arduino-based surf lamp connected to the system via a serial port.

### Environment Variables
```bash
# No environment variables are used in this component.
```
