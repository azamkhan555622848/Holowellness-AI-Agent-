# Gunicorn configuration for memory-optimized deployment
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - CRITICAL: Reduce workers to prevent memory exhaustion
workers = 1  # Single worker to minimize memory usage
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased timeout for ML model loading
keepalive = 2
max_requests = 100  # Restart workers after 100 requests to prevent memory leaks
max_requests_jitter = 10

# Memory optimization
preload_app = True  # Share memory between workers
worker_tmp_dir = "/dev/shm"  # Use RAM disk for worker temp files

# Process naming
proc_name = "holowellness"

# Logging
accesslog = "-"
errorlog = "-" 
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Graceful restarts
graceful_timeout = 30