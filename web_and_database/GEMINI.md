This document describes the roles of the different files in the Surf Lamp web application.

*   **`app.py`**: The main Flask application file. It defines the routes for the web application, including registration, login, and a dashboard. It handles user requests, processes forms, and interacts with the database. It also includes rate limiting to prevent abuse.

*   **`data_base.py`**: This file manages all database interactions. It defines the SQLAlchemy database models (User, Lamp, etc.) and sets up the connection to the PostgreSQL database. It includes the `add_user_and_lamp` function, which is a transactional function to add a new user and their lamp to the database. It can also be run as a script to create the database tables.

*   **`forms.py`**: This file defines the web forms using `Flask-WTF`. It includes the `RegistrationForm` and `LoginForm` with validation rules for each field, such as email format, password strength, and input sanitization. This helps to ensure that the data received from users is valid and secure.

*   **`requirements.txt`**: This file lists all the Python packages that the application depends on. This file is used to install the necessary libraries when setting up the application in a new environment.

*   **`security_config.py`**: This file centralizes security-related configurations for the application. It defines settings for CSRF protection, rate limiting, password policies, and security headers. This makes it easier to manage and review the application's security posture.

*   **`templates/`**: This directory contains the HTML templates for the web application.
    *   **`login.html`**: The template for the user login page.
    *   **`register.html`**: The template for the user registration page.
