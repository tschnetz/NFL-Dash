# app_fast.py
import threading
import uvicorn
import dash
import dash_bootstrap_components as dbc
from flask import Flask
from config import PORT
from layout import layout
from callbacks_fast import register_callbacks
from api import app as fastapi_app
import socket

# Initialize Flask server
server = Flask(__name__)

# Add cache-control headers to prevent browser caching
@server.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Initialize Dash app with Flask server
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP], title="NFL Games")

# Set up layout and callbacks
app.layout = layout
register_callbacks(app)

# Function to check if a port is in use
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

# Function to run FastAPI server
def run_fastapi():
    if not is_port_in_use(8001):
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8001)
    else:
        print("FastAPI server is already running.")

# Start FastAPI server in a separate thread
fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
fastapi_thread.start()

# Run Dash server
if __name__ == "__main__":
    app.run_server(debug=True, port=PORT)