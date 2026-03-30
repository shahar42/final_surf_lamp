"""
Gunicorn configuration for high-concurrency surf lamp web service.
Uses gevent workers for async I/O to handle 10K+ concurrent lamps.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
worker_class = "gevent"  # Async greenlet-based workers
workers = 4  # 4 workers on 512MB Render instance
worker_connections = 1000  # Max concurrent connections per worker
max_requests = 10000  # Restart workers after 10k requests (prevent memory leaks)
max_requests_jitter = 1000  # Add randomness to prevent thundering herd

# Timeouts
timeout = 30  # Request timeout (Arduino polls should be <1s)
keepalive = 5  # Keep-alive for connection reuse

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"
loglevel = "info"

# Server mechanics
preload_app = True  # Load app before forking workers (save memory)
