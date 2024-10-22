# app.py
import dash
import dash_bootstrap_components as dbc
from flask import Flask
from config import PORT
from layout import layout
from callbacks import register_callbacks

# Initialize Flask server
server = Flask(__name__)

# Add cache-control headers to prevent browser caching
@server.after_request
def add_header(response):
    # Disable caching in browsers
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Initialize Dash app with Flask server
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP], title="NFL Games")


# Set up layout and callbacks
app.layout = layout
register_callbacks(app)

# Run the server
if __name__ == "__main__":
    app.run_server(debug=True, port=PORT)