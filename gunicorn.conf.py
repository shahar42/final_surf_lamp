"""
Gunicorn configuration for Surf Lamp
Optimized for Render free tier (512MB RAM)
"""

# Number of worker processes
# 2 for 512MB RAM (safe), can go to 4 if monitoring memory
workers = 2

# Worker class - sync is fine for I/O bound workload (database queries)
worker_class = "sync"

# Worker timeout - kill worker if no response after 30s
timeout = 30

# Max requests per worker before restart (helps prevent memory leaks)
max_requests = 1000

# Randomize max_requests to prevent thundering herd
max_requests_jitter = 50

# Preload app in master process (share memory between workers)
preload_app = True

# Bind to port 10000 (Render default)
bind = "0.0.0.0:10000"

# Access log
accesslog = "-"

# Error log
errorlog = "-"

# Log level
loglevel = "info"

# Keep alive timeout for client connections
keepalive = 2
