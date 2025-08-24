# Archive Debug Files

This directory contains scripts used for debugging and testing various parts of the Surf Lamp project.

## Files

- **`test_openssl_legacy.py`**: A script to test various solutions for the OpenSSL legacy provider issue that can occur when connecting to a PostgreSQL database on Render.
- **`test_tool_debug.py`**: An extreme debug version of a script to diagnose SSL connection issues with a PostgreSQL database. It logs everything to a file.
- **`test_tools.py`**: A script for testing the database tools individually.