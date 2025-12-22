# Decoupling Improvement Plan

To align more closely with "Clean Architecture" principles and ensure the system is robust and testable, the following decoupling improvements are recommended:

## 1. Database Connection Factory
**Current state:** `app.py` handles environment variable parsing, SSL mode string manipulation, and connection instantiation.
**Improvement:** Move connection logic to a dedicated factory in `database.py`.
- **Benefit:** `app.py` should only ask for a connection; it shouldn't care about Render-specific SSL requirements or connection strings.

## 2. File Storage Service
**Current state:** Flask routes directly use `os.path`, `os.remove`, and `file.save`.
**Improvement:** Create a `StorageService` class to handle I/O.
- **Benefit:** Allows switching from local disk to Cloud Storage (AWS S3/Google Cloud Storage) without changing the business logic in `app.py`.

## 3. Remove Driver Leaks
**Current state:** `app.py` specifies `psycopg2.extras.DictCursor`.
**Improvement:** Encapsulate the cursor type within the repository or the database factory.
- **Benefit:** Prevents the web layer from being tied to a specific PostgreSQL driver's implementation details.

## 4. Configuration Object
**Current state:** Routes and functions pull directly from `os.environ`.
**Improvement:** Use a `Config` class to load and validate environment variables at startup.
- **Benefit:** Fails fast if a required variable is missing and provides a single source of truth for settings like `UPLOAD_FOLDER` or `MAX_FILE_SIZE`.

## 5. Domain Models (Optional)
**Current state:** Data passes between layers as raw dictionaries/database rows.
**Improvement:** Define simple Python `Dataclasses` or `Pydantic` models for `Worker` and `Contract`.
- **Benefit:** Provides type hinting and prevents "magic string" bugs when accessing attributes like `worker['name']`.
