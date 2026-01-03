# Kerados Installer Service

Simple Flask web service for hosting the Kerados Windows installer.

## Structure

```
app_installer_service/
├── app.py                          # Flask application
├── requirements.txt                # Python dependencies
├── templates/
│   └── index.html                  # Landing page
└── static/
    └── downloads/
        └── kerados_installer.exe   # Installer file (placeholder currently)
```

## Local Testing

```bash
cd app_installer_service
pip install -r requirements.txt
python app.py
```

Visit: http://localhost:5000

## Deploy to Render

### Option 1: Using MCP Tool (Recommended)

```python
# Use Claude Code's Render MCP tool
mcp__render__create_web_service(
    name="kerados-installer",
    repo_url="https://github.com/<your-username>/Git_Surf_Lamp_Agent",
    build_command="cd app_installer_service && pip install -r requirements.txt",
    start_command="cd app_installer_service && gunicorn app:app",
    env_vars=[],
    branch="master",
    runtime="python"
)
```

### Option 2: Manual Render Dashboard

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `kerados-installer`
   - **Root Directory**: `app_installer_service`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

## Replacing the Placeholder

When the actual installer is ready:

1. Replace `static/downloads/kerados_installer.exe` with the real installer
2. Git commit and push:
   ```bash
   git add app_installer_service/static/downloads/kerados_installer.exe
   git commit -m "Add real Kerados installer"
   git push
   ```
3. Render will auto-deploy the update

## Endpoints

- `GET /` - Landing page with download button
- `GET /download` - Download the installer file
- `GET /health` - Health check for monitoring

## Notes

- Currently uses a placeholder .exe file
- Fully isolated from surf lamp project
- No authentication required (public download)
- Automatic HTTPS via Render
