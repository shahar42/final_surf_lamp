# render.yaml - Render deployment configuration
services:
  # Existing Flask web app
  - type: web
    name: surf-lamp-web
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: surf-lamp-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: REDIS_URL
        fromService:
          type: redis
          name: surf-lamp-redis
          property: connectionString

  # NEW: Background processor (no LLM)
  - type: worker
    name: surf-lamp-processor
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python background_processor.py
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: surf-lamp-db
          property: connectionString
      - key: SURFLINE_API_KEY
        sync: false  # Set manually in Render dashboard
      - key: WEATHER_API_KEY
        sync: false  # Set manually in Render dashboard

  # NEW: Conversational agent (with LLM)
  - type: web
    name: surf-lamp-agent
    env: python
    buildCommand: pip install -r agent_requirements.txt
    startCommand: python conversational_agent.py
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: surf-lamp-db
          property: connectionString
      - key: OPENAI_API_KEY
        sync: false  # Set manually in Render dashboard

databases:
  - name: surf-lamp-db
    databaseName: surfboard_lamp
    user: postgres

  - name: surf-lamp-redis
    type: redis
