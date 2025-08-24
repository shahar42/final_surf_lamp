# Surf Lamp

The Surf Lamp is a multi-component project that brings real-time surf conditions to a physical, network-aware lamp. It combines a web application for user management, a data processor for fetching and interpreting surf data, and an Arduino-based lamp for displaying the conditions.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Project Overview

The Surf Lamp project is designed to provide a simple, at-a-glance indication of current surf conditions. Users can register, configure their location, and the lamp will automatically update to reflect the wave height, period, and wind conditions.

## Features

- **User-friendly Web Interface:** A Flask-based web application for user registration, login, and dashboard management.
- **Real-time Data Processing:** A background processor fetches data from multiple surf and weather APIs.
- **Customizable Hardware:** An Arduino-based lamp that can be easily built and customized.
- **Multi-location Support:** The system can be configured to support multiple surf locations.
- **Secure and Scalable:** The web application uses industry-standard security practices and is designed to be scalable.

## Architecture

The project is divided into three main components:

1.  **`web_and_database`:** A Flask web application that provides the user interface and API endpoints for the system. It handles user authentication, data storage, and serves as the primary point of interaction for users.

2.  **`surf-lamp-processor`:** A Python-based background service that continuously fetches surf data from various APIs, processes it, and sends it to the Arduino lamp.

3.  **`arduino`:** The hardware component of the project. It consists of an Arduino board, a Wi-Fi module, and a set of LEDs to display the surf conditions.

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js and npm (for future development)
- An Arduino IDE and the necessary libraries
- A PostgreSQL database

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repository.git
    cd your-repository
    ```

2.  **Set up the web application:**
    ```bash
    cd web_and_database
    pip install -r requirements.txt
    # Configure your environment variables (e.g., DATABASE_URL, SECRET_KEY)
    flask run
    ```

3.  **Set up the data processor:**
    ```bash
    cd ../surf-lamp-processor
    pip install -r requirements.txt
    # Configure your environment variables (e.g., DATABASE_URL)
    python background_processor.py
    ```

4.  **Set up the Arduino:**
    - Open the `fixed_surf_lamp.ino` file in the Arduino IDE.
    - Install the required libraries.
    - Configure your Wi-Fi credentials and the IP address of the web application.
    - Upload the sketch to your Arduino.

## Usage

1.  **Register an account:** Open your web browser and navigate to the web application's URL. Register a new account and log in.

2.  **Configure your lamp:** In the dashboard, you can set your desired surf location and other preferences.

3.  **Power on your lamp:** Once the lamp is powered on and connected to your Wi-Fi network, it will automatically start receiving data from the processor and displaying the surf conditions.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have any suggestions or find any bugs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
