# api_TESTING - Component Overview

## Purpose & Role
- **What this component does**: This component is used for testing and debugging the Stormglass API integration. It contains scripts to fetch, process, and display surf conditions for various locations.
- **Position in overall architecture**: This is a testing and development component, not part of the production application.
- **Primary responsibility**: To validate API endpoints, test data parsing, and experiment with new features related to surf data retrieval.

## Key Files & Functions
### Critical Files
- `display_surf_conditions.py` - Main script to fetch and display surf conditions.
- `find_cali_points.py` - Contains functions to find surf spots in California.
- `find_more.py` - Contains functions to find additional surf spots.
- `config.ini` - Configuration file for API keys and other settings.
- `successful_cities.json` - Stores a list of cities for which API calls were successful.

### Entry Points
- **Main execution**: The `display_surf_conditions.py` script is the primary entry point for running the tests.
- **API endpoints**: This component does not expose any API endpoints.
- **External interfaces**: This component interacts with the Stormglass API.

## Data Flow
### Inputs
- **Receives from**: This component does not receive data from other components in the project. It is manually triggered.
- **Input format**: The component uses the `successful_cities.json` file as input for which locations to query.
- **Trigger conditions**: This component is activated manually by running the `display_surf_conditions.py` script.

### Outputs
- **Sends to**: This component does not send data to other components. It prints the formatted surf data to the console.
- **Output format**: The output is formatted text displayed in the console.
- **Side effects**: This component may write to the `successful_cities.json` or `successful_cities.txt` files.

## Dependencies & Configuration
### External Dependencies
- **APIs**: This component depends on the Stormglass API for surf data.
- **Network**: Requires an internet connection to access the Stormglass API.

### Environment Variables
```bash
# No environment variables are used in this component. Configuration is handled by the config.ini file.
```
