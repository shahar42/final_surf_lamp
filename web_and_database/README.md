# Web and Database

This directory contains the Flask web application and database-related files for the Surf Lamp project.

## Files

- **`app.py`**: The main Flask web application. It handles user registration, login, the dashboard, and other user-facing routes.
- **`data_base.py`**: This module defines the database schema using SQLAlchemy ORM and provides functions for all database interactions.
- **`forms.py`**: Contains the WTForms classes for the registration and login forms, including validation logic.
- **`security_config.py`**: This file defines security-related configurations for the Flask application, such as CSRF protection, rate limiting, and password requirements.