# layout.py
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc

layout = dbc.Container([
    dcc.Interval(id='interval-scores', interval=30 * 1000, n_intervals=0),
    dcc.Interval(id='interval-odds', interval=60 * 60 * 1000, n_intervals=0),
    dcc.Store(id='in-progress-flag', data=False),
    dcc.Store(id='selected-week', data={'value': None}),
    dcc.Store(id='week-options-store', data=False),
    dcc.Store(id='scores-data', data=[]),
    dcc.Store(id='nfl-events-data', data={}),
    dbc.Row(
        dbc.Col(
            html.Div(
                [
                    html.Img(src="assets/nfl-3644686_1280.webp", height="50px", style={"margin-right": "10px"}),
                    html.H1("NFL Games", style={"display": "inline-block", "vertical-align": "middle"}),
                ],
                style={"display": "flex", "align-items": "center", "justify-content": "center"}
            ),
            width=12,
            className="text-center"
        ),
        style={'margin-bottom': '20px'}
    ),
    dbc.Row(dbc.Col(dcc.Dropdown(
        id='week-selector',
        options=[],
        placeholder="Select a week",
        style={
            'padding': '3px',
            'text-align': 'center',
            'text-align-last': 'center',
            'font-size': '20px',
            'color': 'black',
            'align-items': 'center',
            'justify-content': 'center'
        },
    ))),
    dbc.Row(
        dbc.Col(
            dcc.Loading(
                id='loading',
                type='circle',
                children=[html.Div(id='game-info')]
            )
        )
    ),
])