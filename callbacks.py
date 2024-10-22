# callbacks.py
import dash
import json
from dash.dependencies import Input, Output, State
from dash import html
import dash_bootstrap_components as dbc
from datetime import datetime, timezone
from utils import fetch_nfl_events, fetch_games_by_day, save_last_fetched_odds, load_last_fetched_odds, extract_game_info, get_scoring_plays

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
        week_options = []  # Initialize week_options here

        if week_options_fetched or week_options:  # Check if already fetched or if week_options is not empty
            raise dash.exceptions.PreventUpdate

        # Fetch NFL events once and store them
        data = fetch_nfl_events()
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
        if not week_options_fetched:
            raise dash.exceptions.PreventUpdate

        # print("Initial store_selected_week")
        data = fetch_nfl_events()  # You might not need to fetch the data again here
        leagues_data = data.get('leagues', [])

        selected_value = None  # Initialize selected_value
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
                            break  # Exit the loop once the current week is found

                        week_counter += 1

        # Now you have the selected_value
        # print("Selected Value:", selected_value)
        return {'value': selected_value}

    @app.callback(
        Output('game-info', 'children'),  # Output to the game-info div
        Output('in-progress-flag', 'data'),
        [Input('week-selector', 'value'),
         Input('scores-data', 'data')],  # Ensure scores-data is an input here
        [State('nfl-events-data', 'data')],  # Use stored NFL events data
        prevent_initial_call=True
    )
    def display_game_info(selected_week_index, scores_data, nfl_events_data):

        print("display_game_info triggered!")
        print(f"Scores Data: {scores_data}")

        ctx = dash.callback_context
        triggered_by_week_selection = any(
            'week-selector' in trigger['prop_id'] for trigger in ctx.triggered
        )

        if triggered_by_week_selection:
            print("Week selection triggered, fetching NFL events.")
            nfl_events_data = fetch_nfl_events()

        # if not triggered_by_week_selection and (not scores_data or not any(scores_data)):
        #    print("Preventing update due to no relevant triggers.")
        #    raise dash.exceptions.PreventUpdate

        # Debugging to confirm that correct scores data is being passed
        if scores_data:
            for game in scores_data:
                print(f"Game: {game.get('Home Team')} vs {game.get('Away Team')}")
                print(f"Scores: {game.get('Home Team Score')} - {game.get('Away Team Score')}")
                print(f"Down and Distance: {game.get('Down Distance')}")
                print(f"Possession: {game.get('Possession')}")

        if not nfl_events_data:
            return html.P("No NFL events data available."), False

        # Handle week selection and event data processing
        leagues_data = nfl_events_data.get('leagues', [])
        if not leagues_data:
            return html.P("No leagues data available."), False  # Return False for in-progress flag

        nfl_league = leagues_data[0]
        calendar_data = nfl_league.get('calendar', [])
        week_data = None
        week_counter = 0

        # Find the selected week data
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
            return html.P("Selected week data not found."), False  # Return False for games_in_progress

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

        print("Games in progress:", games_in_progress)

        # Sort the games based on their status
        sorted_games = sorted(selected_week_games, key=lambda x: (
            x['status']['type']['description'] == 'Final',  # Place Final last
            x['status']['type']['description'] == 'Scheduled',  # Place Scheduled next
        ))

        games_info = []
        for game in sorted_games:
            game_info = extract_game_info(game, last_fetched_odds)
            game_id = game.get('id')
            home_color = game_info['Home Team Color']
            away_color = game_info['Away Team Color']

            # Update scores from scores_data, including possession info
            possession_team = None
            down_distance = None
            if 'situation' in game['competitions'][0]:  # Check if the game situation exists
                possession_team_id = game['competitions'][0]['situation'].get('possession', None)
                down_distance = game['competitions'][0]['situation'].get('downDistanceText', '')

                if possession_team_id:
                    if possession_team_id == game['competitions'][0]['competitors'][0]['team']['id']:
                        possession_team = game['competitions'][0]['competitors'][0]['team']['displayName']
                    elif possession_team_id == game['competitions'][0]['competitors'][1]['team']['id']:
                        possession_team = game['competitions'][0]['competitors'][1]['team']['displayName']

            # Conditionally add the football emoji and down distance for the team with possession
            home_team_extra_info = []
            away_team_extra_info = []

            # If home team has possession, display the football emoji and down distance for the home team
            # Refine the possession check and handling for N/A cases
            if possession_team and possession_team != "N/A":
                if possession_team == game_info['Home Team']:
                    home_team_extra_info = [html.H6(["🏈 ", down_distance])]
                elif possession_team == game_info['Away Team']:
                    away_team_extra_info = [html.H6(["🏈 ", down_distance])]
            else:
                # Clear the down distance info if possession is N/A
                home_team_extra_info = []
                away_team_extra_info = []

            # Home and away team score displays (no football emoji here)
            home_team_score_display = [html.H4(game_info['Home Team Score'])]
            away_team_score_display = [html.H4(game_info['Away Team Score'])]

            games_info.append(
                dbc.Button(
                    dbc.Row([
                        dbc.Col(html.Img(src=game_info['Home Team Logo'], height="60px"), width=1,
                                style={'text-align': 'center'}),
                        dbc.Col(
                            html.Div([
                                html.H4(game_info['Home Team'], style={'color': game_info['Home Team Color']}),
                                html.P(f"{game_info['Home Team Record']}", style={'margin': '0', 'padding': '0'}),
                                html.Div(home_team_score_display),  # Display home team score
                                html.P(home_team_extra_info)  # Down distance for home team if possession
                            ], style={'text-align': 'center'}),
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
                            ], style={'text-align': 'center'}),
                            width=4
                        ),
                        dbc.Col(
                            html.Div([
                                html.H4(game_info['Away Team'], style={'color': game_info['Away Team Color']}),
                                html.P(f"{game_info['Away Team Record']}", style={'margin': '0', 'padding': '0'}),
                                html.Div(away_team_score_display),  # Display away team score
                                html.P(away_team_extra_info)  # Down distance for away team if possession
                            ], style={'text-align': 'center'}),
                            width=3
                        ),
                        dbc.Col(html.Img(src=game_info['Away Team Logo'], height="60px"), width=1,
                                style={'text-align': 'center'}),
                    ], className="game-row", style={'padding': '10px'}),
                    id={'type': 'game-button', 'index': game_id},  # Unique ID for each game button
                    n_clicks=0,
                    color='light',
                    className='dash-bootstrap',
                    style={
                        '--team-home-color': home_color + '50',  # Pass team home color
                        '--team-away-color': away_color + '50',  # Pass team away color
                        'width': '100%',
                        'text-align': 'left'
                    },
                    value=game_id,  # Pass the game_id as the button's value
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
        # Fetch data for all games on the selected day
        print("Updating scores data...")
        games_data = fetch_games_by_day()

        if not games_data:
            print("No games data found.")
            return dash.no_update, False  # No games, no need to update

        updated_scores_data = []
        games_in_progress = False

        # Iterate through the list of games and extract score data
        for game in games_data.get('events', []):
            game_id = game.get('id')
            competitions = game.get('competitions', [])

            if not competitions:
                print(f"No competitions found for game ID {game_id}")
                continue

            # Extract relevant game details
            home_team = competitions[0]['competitors'][0]['team']['displayName']
            away_team = competitions[0]['competitors'][1]['team']['displayName']
            home_score = competitions[0]['competitors'][0].get('score', 'N/A')
            away_score = competitions[0]['competitors'][1].get('score', 'N/A')

            # Game status and other details
            status_info = competitions[0].get('status', {})
            quarter = status_info.get('period', 'N/A')
            time_remaining = status_info.get('displayClock', 'N/A')
            game_status = status_info.get('type', {}).get('description', 'N/A')

            # Fetch possession details
            situation = competitions[0].get('situation', {})
            possession = situation.get('downDistanceText', 'N/A')
            possession_team = situation.get('possessionText', 'N/A')

            # Print game details regardless of game status
            print(f"{home_team} vs {away_team}: {quarter} quarter, {time_remaining}")
            print(f"Score: {home_team} {home_score} - {away_team} {away_score}")
            print(f"Current Possession: {possession_team} - {possession}")

            # If game is in progress, mark as true
            if game_status.lower() == "in progress":
                games_in_progress = True

            # Append the extracted data to updated_scores_data
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

        # Compare the new scores with the previous ones to avoid unnecessary updates
        if prev_scores_data == updated_scores_data:
            print("No updates needed.")
            return dash.no_update, games_in_progress  # No need to update if the scores haven't changed

        print("Scores updated.")
        return updated_scores_data, games_in_progress


    @app.callback(
        Output({'type': 'scoring-plays', 'index': dash.dependencies.ALL}, 'children'),
        [Input({'type': 'game-button', 'index': dash.dependencies.ALL}, 'n_clicks')],
        [State({'type': 'game-button', 'index': dash.dependencies.ALL}, 'id')]
    )
    def display_scoring_plays(n_clicks_list, button_ids):
        ctx = dash.callback_context
        if not ctx.triggered:
            return [[]] * len(n_clicks_list)

        # Get the triggered button ID
        triggered_button = ctx.triggered[0]['prop_id'].split('.')[0]
        game_id = json.loads(triggered_button)['index']  # Get the game ID from button ID

        # Fetch and display scoring plays for the selected game
        scoring_plays = get_scoring_plays(game_id)

        # Ensure the scoring plays are displayed for the correct game button
        outputs = []
        for i, button_id in enumerate(button_ids):
            if n_clicks_list[i] % 2 == 1:  # Show scoring plays if clicked
                outputs.append(scoring_plays)
            else:
                outputs.append([])  # Hide scoring plays if not clicked

        return outputs
