# Web Dashboard and API

This directory contains the Flask web application that serves as the primary user interface and API for the Surf Lamp project.

## Overview

The application provides a web-based dashboard for users to register, log in, and view the real-time status and surf conditions of their lamp. It also exposes a set of API endpoints that are used by the Arduino devices for service discovery and data synchronization.

## Features

*   **User Authentication:** Secure user registration, login, and password reset functionality.
*   **Interactive Dashboard:** Displays the latest surf data, lamp status, and user preferences.
*   **Device API:** Provides endpoints for Arduinos to dynamically discover the server, pull the latest data, and report their status.
*   **Security:** Implements rate limiting on sensitive endpoints, sanitizes all user input, and uses secure password hashing.

## Technology Stack

*   **Backend:** Flask
*   **Database:** PostgreSQL (with SQLAlchemy for ORM)
*   **Authentication:** Flask-Bcrypt for password hashing, Flask-WTF for secure forms.
*   **Rate Limiting:** Flask-Limiter with a Redis backend.
*   **Deployment:** Gunicorn (for production)

## Database Schema

The database is the backbone of the application. The schema is defined in `data_base.py` and includes the following key tables:

*   `users`: Stores user credentials, preferences (theme, units), and their selected location.
*   `lamps`: Represents each physical lamp device and links it to a user.
*   `current_conditions`: A table that stores the latest processed surf data for each lamp. This table is written to by the `surf-lamp-processor` and read by the web app to display on the dashboard.
*   `usage_lamps` & `daily_usage`: These tables manage the complex mapping between lamps and the multiple API sources required to gather full surf data for a given location.

## API Endpoints for Devices

The application exposes several endpoints for the Arduino devices:

*   `GET /api/discovery/server`
    *   **Purpose:** Allows a device to dynamically find the active server address. This is the first endpoint a device should call.
*   `GET /api/arduino/<arduino_id>/data`
    *   **Purpose:** Allows a device to **pull** the latest processed surf data from the server. This is the recommended data synchronization method.
*   `POST /api/arduino/callback`
    *   **Purpose:** Allows a device to **push** its status (including its local IP address) back to the server. This is useful for monitoring and debugging.

## Setup and Running

### 1. Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

This service is configured using environment variables. Create a `.env` file in this directory or set the variables directly in your shell.

| Variable          | Description                                                                  |
| ----------------- | ---------------------------------------------------------------------------- |
| `DATABASE_URL`    | **Required.** The connection string for the PostgreSQL database.             |
| `SECRET_KEY`      | **Required.** A long, random string used for signing session cookies.        |
| `REDIS_URL`       | **Required.** The connection string for your Redis instance.                 |
| `MAIL_SERVER`     | **Required for password reset.** The SMTP server for sending emails.         |
| `MAIL_PORT`       | **Required for password reset.** The port of the SMTP server.                |
| `MAIL_USERNAME`   | **Required for password reset.** The username for the SMTP server.           |
| `MAIL_PASSWORD`   | **Required for password reset.** The password for the SMTP server.           |
| `MAIL_DEFAULT_SENDER` | **Required for password reset.** The email address to send from.             |

### 3. Initialize the Database

Before running the application for the first time, you need to create the database tables. Run the following command:

```bash
python data_base.py
```

### 4. Running the Application

**For development:**

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5001`.

**For production:**

Use the Gunicorn WSGI server:

```bash
gunicorn app:app
```
