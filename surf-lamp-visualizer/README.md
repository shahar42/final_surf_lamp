# Surf Lamp System Visualizer

Interactive D3.js visualization of the Surf Lamp IoT system architecture.

## Features

- **Force-directed graph** showing all system modules as interconnected nodes
- **Interactive tooltips** with detailed module descriptions
- **Animated data flow** with pulsing nodes showing real-time system cycles
- **Zoom and pan** to explore different parts of the architecture
- **Drag nodes** to rearrange the layout
- **Color-coded modules** by type (backend, hardware, storage, etc.)
- **System statistics** showing key metrics

## Architecture Visualization

Displays:
- Web Application (Flask backend)
- Background Processor (20-min cycles)
- Arduino Lamps (13-min polling)
- Database (Supabase/PostgreSQL)
- Redis Cache (rate limiting)
- External APIs (weather data sources)
- MCP Tools (debugging & monitoring)
- ServerDiscovery (dynamic config)

## Local Development

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5000

## Deployment to Render

### Option 1: Blueprint Deploy (Automatic)

```bash
# From project root
render blueprint launch
```

### Option 2: Manual Deploy

1. Push to GitHub
2. Go to Render Dashboard
3. New → Web Service
4. Connect repository: `Git_Surf_Lamp_Agent/surf-lamp-visualizer`
5. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Health Check Path**: `/api/health`

## API Endpoints

- `GET /` - Main visualization page
- `GET /api/system-data` - System architecture graph data (JSON)
- `GET /api/stats` - System statistics (JSON)
- `GET /api/health` - Health check for monitoring

## Tech Stack

- **Backend**: Flask + Gunicorn
- **Frontend**: D3.js v7 (force simulation)
- **Styling**: Vanilla CSS with gradients
- **Deployment**: Render (free tier compatible)

## Future Enhancements

- [ ] Real-time data integration with Supabase
- [ ] Live lamp locations on map
- [ ] Historical API call patterns
- [ ] Performance metrics overlay
- [ ] WebSocket for live updates
- [ ] Virtual LED strip simulator

---

*Part of the Surf Lamp IoT system - See main system docs at [system_design.md](../system_design.md)*