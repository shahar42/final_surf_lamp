# Broken Tools

This file documents tools that were found to be non-functional during the service recovery on September 26, 2025.

- **`update_service_env_vars`** - **REMOVED**
  - **Issue**: Consistently failed with a `400: {"message":"invalid JSON"}` error from the Render API, even with valid input.
  - **Resolution**: Tool has been permanently removed from the codebase due to unfixable API compatibility issues.
  - **Workaround**: Use service recreation with `create_web_service` or `create_background_worker` tools to set environment variables during creation.
