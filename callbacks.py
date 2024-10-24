# callbacks.py
import dash
import json
from dash.dependencies import Input, Output, State
from dash import html
import dash_bootstrap_components as dbc
from datetime import datetime, timezone
import requests
from utils import save_last_fetched_odds, load_last_fetched_odds, extract_game_info

last_fetched_odds = load_last_fetched_odds()

def register_callbacks(app):
    @app.callback(
        Output('week-selector', 'options'),
        Output('week-options-store', 'data'),
        Output('week-selector', 'value'),
        Output('nfl-events-data', 'data'),
        [Input('week-options-store', 'data')]
    )
    def update_week_options(week_options_fetched):
        print("update_week_options triggered")
        week_options = []  # Initialize week_options here

        if week_options_fetched or week_options:  # Check if already fetched or if week_options is not empty
            raise dash.exceptions.PreventUpdate

        # Fetch NFL events once and store them
        response = requests.get("http://127.0.0.1:8001/nfl-events")  # Updated port to 8001
        data = response.json() if response.status_code == 200 else {}
        leagues_data = data.get('leagues', [])

        if not leagues_data:
            return [], False, None, {}

        nfl_league = leagues_data[0]
        calendar_data = nfl_league.get('calendar', [])
        week_options = []
        selected_value = None
        current_date = datetime.now(timezone.utc)

        week_counter = 0
        for period in calendar_data:
            if 'entries' in period:
                for week in period['entries']:
                    start_date = datetime.fromisoformat(week['startDate'][:-1]).replace(tzinfo=timezone.utc)
                    end_date = datetime.fromisoformat(week['endDate'][:-1]).replace(tzinfo=timezone.utc)
                    week_label = f"{week['label']}: {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"

                    week_options.append({'label': week_label, 'value': week_counter})

                    if start_date <= current_date <= end_date:
                        selected_value = week_counter

                    week_counter += 1

        if selected_value is None and week_options:
            selected_value = week_options[0]['value']

        return week_options, True, selected_value, data  # Return the fetched data to store it


    @app.callback(
        Output('selected-week', 'data'),
        [Input('week-options-store', 'data')]
    )
    def store_selected_week(week_options_fetched):
        print("store_selected_week triggered")
        if not week_options_fetched:
            raise dash.exceptions.PreventUpdate

        data = requests.get("http://127.0.0.1:8001/nfl-events").json()  # Updated port to 8001
        leagues_data = data.get('leagues', [])

        selected_value = None
        if leagues_data:
            nfl_league = leagues_data[0]
            calendar_data = nfl_league.get('calendar', [])
            current_date = datetime.now(timezone.utc)

            week_counter = 0
            for i, period in enumerate(calendar_data):
                if 'entries' in period:
                    for week in period['entries']:
                        start_date = datetime.fromisoformat(week['startDate'][:-1]).replace(tzinfo=timezone.utc)
                        end_date = datetime.fromisoformat(week['endDate'][:-1]).replace(tzinfo=timezone.utc)

                        if start_date <= current_date <= end_date:
                            selected_value = week_counter
                            break

                        week_counter += 1

        return {'value': selected_value}


    @app.callback(
        Output('game-info', 'children'),
        Output('in-progress-flag', 'data'),
        [Input('week-selector', 'value'),
         Input('scores-data', 'data')],
        [State('nfl-events-data', 'data')],
        prevent_initial_call=True
    )
    def display_game_info(selected_week_index, scores_data, nfl_events_data):
        print("display_game_info triggered")
        print(f"Scores Data: {scores_data}")

        ctx = dash.callback_context
        triggered_by_week_selection = any(
            'week-selector' in trigger['prop_id'] for trigger in ctx.triggered
        )

        if triggered_by_week_selection:
            print("Week selection triggered, fetching NFL events.")
            nfl_events_data = requests.get("http://127.0.0.1:8001/nfl-events").json()  # Updated port to 8001

        if scores_data:
            for game in scores_data:
                print(f"Game: {game.get('Home Team')} vs {game.get('Away Team')}")
                print(f"Scores: {game.get('Home Team Score')} - {game.get('Away Team Score')}")
                print(f"Down and Distance: {game.get('Down Distance')}")
                print(f"Possession: {game.get('Possession')}")

        if not nfl_events_data:
            return html.P("No NFL events data available."), False

        leagues_data = nfl_events_data.get('leagues', [])
        if not leagues_data:
            return html.P("No leagues data available."), False

        nfl_league = leagues_data[0]
        calendar_data = nfl_league.get('calendar', [])
        week_data = None
        week_counter = 0

        for period in calendar_data:
            if 'entries' in period:
                for week in period['entries']:
                    if week_counter == selected_week_index:
                        week_data = week
                        break
                    week_counter += 1
            if week_data:
                break

        if not week_data:
            return html.P("Selected week data not found."), False

        week_start = datetime.fromisoformat(week_data['startDate'][:-1]).replace(tzinfo=timezone.utc)
        week_end = datetime.fromisoformat(week_data['endDate'][:-1]).replace(tzinfo=timezone.utc)

        events_data = nfl_events_data.get('events', [])
        selected_week_games = [
            event for event in events_data
            if week_start <= datetime.fromisoformat(event['date'][:-1]).replace(tzinfo=timezone.utc) <= week_end
        ]
        games_in_progress = any(game['status']['type']['description'] != 'Scheduled' or
                                game['status']['type']['description'] != 'Final'
                                for game in selected_week_games)

        sorted_games = sorted(selected_week_games, key=lambda x: (
            x['status']['type']['description'] == 'Final',
            x['status']['type']['description'] == 'Scheduled',
        ))

        games_info = []
        for game in sorted_games:
            game_info = extract_game_info(game, last_fetched_odds)
            game_id = game.get('id')
            home_color = game_info['Home Team Color']
            away_color = game_info['Away Team Color']

            possession_team = None
            down_distance = None
            if 'situation' in game['competitions'][0]:
                possession_team_id = game['competitions'][0]['situation'].get('possession', None)
                down_distance = game['competitions'][0]['situation'].get('downDistanceText', '')

                if possession_team_id:
                    if possession_team_id == game['competitions'][0]['competitors'][0]['team']['id']:
                        possession_team = game['competitions'][0]['competitors'][0]['team']['displayName']
                    elif possession_team_id == game['competitions'][0]['competitors'][1]['team']['id']:
                        possession_team = game['competitions'][0]['competitors'][1]['team']['displayName']

            home_team_extra_info = []
            away_team_extra_info = []

            if possession_team and possession_team != "N/A":
                if possession_team == game_info['Home Team']:
                    home_team_extra_info = [html.H6(["🏈 ", down_distance])]
                elif possession_team == game_info['Away Team']:
                    away_team_extra_info = [html.H6(["🏈 ", down_distance])]
            else:
                home_team_extra_info = []
                away_team_extra_info = []

            home_team_score_display = [html.H4(game_info['Home Team Score'])]
            away_team_score_display = [html.H4(game_info['Away Team Score'])]

            games_info.append(
                dbc.Button(
                    dbc.Row([
                        dbc.Col(html.Img(src=game_info['Home Team Logo'], height="60px"), width=1,
                                style={'textAlign': 'center'}),
                        dbc.Col(
                            html.Div([
                                html.H4(game_info['Home Team'], style={'color': game_info['Home Team Color']}),
                                html.P(f"{game_info['Home Team Record']}", style={'margin': '0', 'padding': '0'}),
                                html.Div(home_team_score_display),
                                html.P(home_team_extra_info)
                            ], style={'textAlign': 'center'}),
                            width=3
                        ),
                        dbc.Col(
                            html.Div([
                                html.H5(game_info['Game Status']),
                                (html.H6(f"{game_info['Quarter']} Qtr, {game_info['Time Remaining']} remaining")
                                 if game_info['Game Status'] == 'In Progress' else ""),
                                html.H6(game_info['Odds']) if game_info['Odds'] else "",
                                html.P(game_info['Start Date (EST)'], style={'margin': '0', 'padding': '0'}),
                                html.P(f"{game_info['Location']} - {game_info['Network']}",
                                       style={'margin': '0', 'padding': '0'}),
                            ], style={'textAlign': 'center'}),
                            width=4
                        ),
                        dbc.Col(
                            html.Div([
                                html.H4(game_info['Away Team'], style={'color': game_info['Away Team Color']}),
                                html.P(f"{game_info['Away Team Record']}", style={'margin': '0', 'padding': '0'}),
                                html.Div(away_team_score_display),
                                html.P(away_team_extra_info)
                            ], style={'textAlign': 'center'}),
                            width=3
                        ),
                        dbc.Col(html.Img(src=game_info['Away Team Logo'], height="60px"), width=1,
                                style={'textAlign': 'center'}),
                    ], className="game-row", style={'padding': '10px'}),
                    id={'type': 'game-button', 'index': game_id},
                    n_clicks=0,
                    color='light',
                    className='dash-bootstrap',
                    style={
                        '--team-home-color': home_color + '50',
                        '--team-away-color': away_color + '50',
                        'width': '100%',
                        'textAlign': 'left'
                    },
                    value=game_id,
                )
            )
            games_info.append(html.Div(id={'type': 'scoring-plays', 'index': game_id}, children=[]))
            games_info.append(html.Hr())

        return games_info, games_in_progress


    @app.callback(
        Output('scores-data', 'data'),
        Output('in-progress-flag', 'data', allow_duplicate=True),
        [Input('interval-scores', 'n_intervals')],
        [State('scores-data', 'data')],
        prevent_initial_call=True
    )
    def update_scores(n_intervals, prev_scores_data):
        print(f"Interval triggered: {n_intervals}")
        response = requests.get("http://127.0.0.1:8001/nfl-scoreboard-day")  # Updated port to 8001
        games_data = response.json() if response.status_code == 200 else {}

        if not games_data:
            print("No games data found.")
            return dash.no_update, False

        updated_scores_data = []
        games_in_progress = False

        for game in games_data.get('events', []):
            game_id = game.get('id')
            competitions = game.get('competitions', [])

            if not competitions:
                print(f"No competitions found for game ID {game_id}")
                continue

            home_team = competitions[0]['competitors'][0]['team']['displayName']
            away_team = competitions[0]['competitors'][1]['team']['displayName']
            home_score = competitions[0]['competitors'][0].get('score', 'N/A')
            away_score = competitions[0]['competitors'][1].get('score', 'N/A')

            status_info = competitions[0].get('status', {})
            quarter = status_info.get('period', 'N/A')
            time_remaining = status_info.get('displayClock', 'N/A')
            game_status = status_info.get('type', {}).get('description', 'N/A')

            situation = competitions[0].get('situation', {})
            possession = situation.get('downDistanceText', 'N/A')
            possession_team = situation.get('possessionText', 'N/A')

            print(f"{home_team} vs {away_team}: {quarter} quarter, {time_remaining}")
            print(f"Score: {home_team} {home_score} - {away_team} {away_score}")
            print(f"Current Possession: {possession_team} - {possession}")

            if game_status.lower() == "in progress":
                games_in_progress = True

            updated_scores_data.append({
                'game_id': game_id,
                'Home Team': home_team,
                'Away Team': away_team,
                'Home Team Score': home_score,
                'Away Team Score': away_score,
                'Quarter': quarter,
                'Time Remaining': time_remaining,
                'Down Distance': possession,
                'Possession': possession_team,
            })

        if prev_scores_data == updated_scores_data:
            print("No updates needed.")
            return dash.no_update, games_in_progress

        print("Scores updated.")
        return updated_scores_data, games_in_progress


    @app.callback(
        Output({'type': 'scoring-plays', 'index': dash.dependencies.ALL}, 'children'),
        [Input({'type': 'game-button', 'index': dash.dependencies.ALL}, 'n_clicks')],
        [State({'type': 'game-button', 'index': dash.dependencies.ALL}, 'id')]
    )
    def display_scoring_plays(n_clicks_list, button_ids):
        print("display_scoring_plays triggered")

        ctx = dash.callback_context
        if not ctx.triggered:
            return [[]] * len(n_clicks_list)

        triggered_button = ctx.triggered[0]['prop_id'].split('.')[0]
        game_id = json.loads(triggered_button)['index']

        response = requests.get(f"http://127.0.0.1:8001/nfl-scoringplays?game_id={game_id}")  # Updated port to 8001
        scoring_plays = response.json() if response.status_code == 200 else []

        outputs = []
        for i, button_id in enumerate(button_ids):
            if n_clicks_list[i] % 2 == 1:
                formatted_scoring_plays = []
                for play in scoring_plays:
                    team_logo = play['team'].get('logo', '')
                    period = play.get('period', {}).get('number', '')
                    clock = play.get('clock', {}).get('displayValue', '')
                    text = play.get('text', '')
                    away_score = play.get('awayScore', 'N/A')
                    home_score = play.get('homeScore', 'N/A')

                    formatted_play = html.Div([
                        html.Img(src=team_logo, height="30px", style={'margin-right': '10px'}),
                        html.Span(f"Q{period} {clock} - "),
                        html.Span(text),
                        html.Span(f" ({away_score} - {home_score})", style={'margin-left': '10px'})
                    ], style={'display': 'flex', 'align-items': 'center'})

                    formatted_scoring_plays.append(formatted_play)

                outputs.append(formatted_scoring_plays)
            else:
                outputs.append([])

        return outputs