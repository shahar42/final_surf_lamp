# Web Application and Database

This directory contains the core web application for the Surf Lamp project. It is a Flask-based application that provides the user-facing dashboard, authentication, and the API endpoint for the Arduino devices.

## Overview

The application serves three main purposes:

1.  **User Management:** Handles user registration, login, and password management.
2.  **Dashboard:** Provides a user-specific dashboard to view surf conditions, manage lamp settings (like location and alert thresholds), and see device status.
3.  **Arduino API:** Exposes a `GET` endpoint that allows a registered Arduino device to pull its specific surf data and configuration.

## 🛠️ Local Development Setup

Follow these steps to run the web application on your local machine for development.

### Prerequisites

*   **Python:** Version 3.8 or newer.
*   **PostgreSQL:** A running PostgreSQL database server.
*   **Redis:** A running Redis server (for rate limiting and caching).

### Installation

1.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration (Environment Variables)

The application is configured using environment variables. Create a file named `.env` in this directory and add the following key-value pairs. **Do not commit this file to version control.**

```ini
# .env file

# A strong, random string for signing session cookies
SECRET_KEY='your-very-strong-secret-key'

# Connection string for your PostgreSQL database
DATABASE_URL='postgresql://user:password@localhost/surf_lamp_db'

# Connection string for your Redis server
REDIS_URL='redis://localhost:6379'

# Email configuration for password resets
MAIL_SERVER='smtp.gmail.com'
MAIL_PORT=587
MAIL_USERNAME='your-email@gmail.com'
MAIL_PASSWORD='your-app-password'
MAIL_DEFAULT_SENDER='your-email@gmail.com'
```

### Running the Application

Once the dependencies are installed and the `.env` file is configured, you can start the development server:

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5001`.

## 🚀 Production Deployment (Render)

This application is designed to be deployed on platforms like Render.

*   **Service Type:** Deploy as a **Web Service**.
*   **Build Command:** `pip install -r web_and_database/requirements.txt`
*   **Start Command:** `gunicorn web_and_database.app:app`

#### Environment Variables

In the Render dashboard, create environment variables with the same keys and values as in the local `.env` file, but using your production database, Redis, and email credentials.

#### ProxyFix Middleware

The application includes `ProxyFix` middleware, which is essential for running behind a reverse proxy like Render's. It ensures that Flask correctly handles `X-Forwarded-For` and `X-Forwarded-Proto` headers, which is critical for security features and generating correct redirect URLs.

## 🔒 Security Best Practices

Several security measures are built into the application:

*   **Password Hashing:** User passwords are never stored in plaintext. They are hashed using `Flask-Bcrypt`.
*   **CSRF Protection:** `Flask-WTF` is used to generate and validate CSRF tokens for all forms, protecting against Cross-Site Request Forgery attacks.
*   **Rate Limiting:** `Flask-Limiter` is configured to prevent brute-force attacks on authentication routes (`/login`, `/register`, `/forgot-password`).
*   **Secure Sessions:** User sessions are cryptographically signed using the `SECRET_KEY`.

## 📂 Project Structure

*   `app.py`: The main Flask application file containing all routes and application logic.
*   `data_base.py`: Defines the SQLAlchemy database models and includes functions for interacting with the database.
*   `forms.py`: Defines the WTForms classes used for registration, login, and password reset.
*   `requirements.txt`: A list of all Python dependencies.
*   `templates/`: Contains all the HTML templates rendered by Flask.
*   `static/`: Contains static assets like CSS, JavaScript, and images.