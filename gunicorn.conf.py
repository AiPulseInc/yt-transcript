# Gunicorn configuration file
# Optimized for Render's free tier with limited memory

# Server socket
bind = "0.0.0.0:10000"
backlog = 256

# Worker processes - reduced for lower memory usage
workers = 2  # Reduced from dynamic calculation
worker_class = 'sync'
worker_connections = 200
timeout = 120
keepalive = 2

# Reduce worker memory usage
max_requests = 250
max_requests_jitter = 50

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'gunicorn_process'

# Worker timeout
graceful_timeout = 120

# Reduce buffer size
worker_tmp_dir = '/dev/shm'
