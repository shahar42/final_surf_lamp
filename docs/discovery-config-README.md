# Server Discovery Configuration

This directory contains the configuration file that allows deployed Arduino devices to dynamically discover the location of the production backend server. This is a critical component for system resilience, as it allows the backend to be migrated to a new server without needing to re-flash the entire fleet of devices.

## Overview

The `ServerDiscovery.h` class in the Arduino firmware is programmed to fetch the `config.json` file from a public URL hosted on GitHub Pages. It parses this file to find the primary API server. If this process fails, it falls back to a hardcoded list of servers.

## Configuration File Format (`config.json`)

The `config.json` file defines the server landscape for the devices.

### Example

```json
{
  "api_server": "final-surf-lamp.onrender.com",
  "backup_servers": [
    "backup-api.herokuapp.com",
    "api.surflamp.com"
  ],
  "version": "1.0",
  "timestamp": 1692847200,
  "endpoints": {
    "arduino_data": "/api/arduino/{arduino_id}/data",
    "status": "/api/arduino/status"
  },
  "update_interval_hours": 24,
  "signature": "unsigned_for_now"
}
```

### Field Descriptions

| Field                   | Type          | Description                                                                                             |
| ----------------------- | ------------- | ------------------------------------------------------------------------------------------------------- |
| `api_server`            | String        | **Required.** The primary domain name of the production server that devices should contact.             |
| `backup_servers`        | Array of Strings | A list of secondary servers. This is currently for informational purposes; the firmware uses its own hardcoded fallbacks. |
| `version`               | String        | The version of the configuration file.                                                                  |
| `timestamp`             | Integer       | A Unix timestamp indicating when the file was last updated.                                             |
| `endpoints`             | Object        | Defines the specific API paths. This allows for changing API routes without a firmware update.          |
| `update_interval_hours` | Integer       | Informs the device how often it should check for a new discovery file. The device caches the server address. |
| `signature`             | String        | (Future Use) A cryptographic signature to verify the authenticity of the file.                          |

## 🚀 Deployment to GitHub Pages

For the discovery mechanism to work, this `config.json` file must be accessible via a public URL. GitHub Pages is a free and reliable way to achieve this.

1.  **Navigate to Repository Settings:** In your GitHub repository, go to `Settings` > `Pages`.
2.  **Configure Source:** Under "Build and deployment", select `Deploy from a branch`.
3.  **Select Branch:** Choose the `main` (or `master`) branch and the `/docs` folder as the source, or `/ (root)` if you prefer.
4.  **Save:** Click `Save`. GitHub will generate a public URL for your repository's content (e.g., `https://your-username.github.io/your-repo/`).

Once set up, any changes pushed to the selected branch will be automatically published and live on your GitHub Pages site.

## 🔄 Update Procedure

To direct all devices to a new server (e.g., after a migration), follow these steps:

1.  **Edit the File:** Change the value of the `api_server` key in `config.json` to the new server address.
    ```json
    "api_server": "new-production-server.onrender.com",
    ```
2.  **Commit and Push:** Commit the change to your `main` (or `master`) branch and push it to GitHub.
    ```bash
    git add discovery-config/config.json
    git commit -m "Update production API server to new-production-server.onrender.com"
    git push origin main
    ```
3.  **Wait for Propagation:** Devices will automatically pick up the new server address the next time their 24-hour discovery cache expires. This will happen gradually across the fleet, resulting in a smooth, rolling migration.

## 🛡️ Backup and Rollback Strategies

### Backup

The primary backup mechanism is built into the firmware itself. In `ServerDiscovery.h`, there is a hardcoded list of fallback servers. If the device fails to fetch or parse the `config.json` file from GitHub for any reason, it will iterate through this hardcoded list, providing a high degree of resilience.

### Rollback

Rolling back a server change is straightforward and leverages Git's history.

1.  **Identify the Commit:** Find the commit hash of the incorrect server change using `git log`.
2.  **Revert the Commit:** Use `git revert` to create a new commit that undoes the changes from the bad commit.
    ```bash
    git revert <commit-hash-of-bad-change>
    ```
3.  **Push the Revert:** Push the newly created revert commit to the `main` branch.

This will publish a new `config.json` with the previous, correct server address, and devices will migrate back on their next discovery cycle.
