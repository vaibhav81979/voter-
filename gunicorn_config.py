"""
Gunicorn configuration for National E-Voting Portal
Uses eventlet worker class required by Flask-SocketIO
"""

import os

# Worker class — MUST be eventlet for Flask-SocketIO
worker_class = "eventlet"
workers = 1  # SocketIO state is not shared — keep at 1

# Binding
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Logging
loglevel = "info"
accesslog = "-"
errorlog  = "-"
capture_output = True

# Timeouts
timeout = 120
keepalive = 5

# Security
limit_request_line = 4094
limit_request_fields = 100
