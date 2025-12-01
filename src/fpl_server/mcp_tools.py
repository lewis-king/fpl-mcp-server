import uuid
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from .state import store
from .models import TransferPayload
from .rotowire_scraper import RotoWireLineupScraper

# Define the server
mcp = FastMCP("FPL Manager")
BASE_URL = "http://localhost:8000"

# Global session tracking - stores the active session after login
_active_session_id: str | None = None

def _get_client():
    """Internal helper to get the active client"""
    if not _active_session_id:
        return None
    return store.get_client(_active_session_id)

@mcp.tool()
async def login_to_fpl() -> str:
    """
    Step 1: Generates a secure login link. 
    Call this when the user wants to log in or when other tools return 'Authentication required'.
    After successful login, your session will be automatically activated.
    """
    request_id = str(uuid.uuid4())
    store.create_login_request(request_id)
    
    return (
        f"Please authenticate here: {BASE_URL}/login/{request_id}\n\n"
        f"INSTRUCTION: Wait for the user to confirm they have finished logging in. "
        f"Then, immediately call 'check_login_status' with ID: {request_id}"
    )

@mcp.tool()
async def check_login_status(request_id: str) -> str:
    """
    Step 2: Checks if the user has completed the web login. 
    On success, automatically activates your session for all future tool calls.
    """
    global _active_session_id
    
    req = store.pending_logins.get(request_id)
    if not req:
        return "Error: Invalid Request ID"
    
    if req.status == "pending":
        return "Login pending. Waiting for user..."
    if req.status == "failed":
        return f"Login failed: {req.error}"
    
    # Store the session ID globally
    _active_session_id = req.session_id
    
    client = _get_client()
    if client and client.user_info:
        user_entry = client.user_info.get('player', {}).get('entry')
        return (
            f"✅ Authentication Successful!\n"
            f"Your session is now active. You can now use all FPL tools without providing a session ID.\n"
            f"Your FPL entry has been loaded automatically."
        )
    
    return "✅ Authentication Successful! Your session is now active."

@mcp.tool()
async def get_my_info() -> str:
    """
    Get your FPL account information including entry ID, leagues, and basic stats.
    Use this to see what leagues you're in and your overall performance.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not client.user_info:
        return "Error: User information not available. Please try logging in again."
    
    try:
        player_info = client.user_info.get('player', {})
        leagues = client.user_info.get('leagues', {})
        classic_leagues = leagues.get('classic', [])
        
        output = [
            f"**Your FPL Account**",
            f"Name: {player_info.get('first_name')} {player_info.get('last_name')}",
            f"Region: {player_info.get('region_name')} ({player_info.get('region_iso_code_short')})",
            ""
        ]
        
        if classic_leagues:
            output.append(f"**Your Leagues ({len(classic_leagues)}):**")
            for league in classic_leagues[:10]:  # Show first 10
                output.append(f"├─ {league.get('name')}")
            if len(classic_leagues) > 10:
                output.append(f"└─ ... and {len(classic_leagues) - 10} more")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_my_squad() -> str:
    """Get your current team squad and bank balance."""
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        entry_id = store.get_user_entry_id(client)
        if not entry_id:
            return "Error: Could not determine your entry ID. Please try logging in again."
        
        my_team = await client.get_my_team(entry_id)
        all_players = await client.get_players()
        p_map = {p.id: p for p in all_players}
        
        bank = my_team['transfers']['bank'] / 10
        output = [f"**My Team (Bank: £{bank}m)**"]
        
        for pick in my_team['picks']:
            p = p_map.get(pick['element'])
            role = " (C)" if pick['is_captain'] else " (VC)" if pick['is_vice_captain'] else ""
            output.append(f"- {p.web_name} ({p.team_name}): £{pick['selling_price']/10}m {role}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def search_players(name_query: str) -> str:
    """
    Search for players by name. Returns price, form, and basic stats.
    Use player names (not IDs) for all operations.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    players = await client.get_players()
    matches = [p for p in players if name_query.lower() in p.web_name.lower()]
    
    if not matches: return "No players found."
    
    return "\n".join([
        f"{p.web_name} ({p.team_name}) | £{p.price}m | Form: {p.form}" 
        for p in matches[:10]
    ])

@mcp.tool()
async def get_top_players() -> str:
    """
    Get top performing players by position (GKP, DEF, MID, FWD) based on points per game.
    Returns top 3 goalkeepers and top 10 for each outfield position.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        top_players = await client.get_top_players_by_position()
        
        output = ["**Top Players by Position (Points per Game)**\n"]
        
        for position, players in top_players.items():
            if not players:
                continue
            output.append(f"\n**{position}:**")
            for p in players:
                news_indicator = " ⚠️" if p['news'] else ""
                output.append(
                    f"├─ {p['name']} ({p['team']}) - £{p['price']:.1f}m | "
                    f"PPG: {p['points_per_game']:.1f} | Total: {p['total_points']}{news_indicator}"
                )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def make_transfers(player_names_out: list[str], player_names_in: list[str]) -> str:
    """
    Execute transfers using player names. IRREVERSIBLE.
    Provide lists of player names to transfer out and in.
    Example: player_names_out=["Salah"], player_names_in=["Haaland"]
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if len(player_names_out) != len(player_names_in):
        return "Error: Number of players out must match number of players in."
    
    try:
        # Resolve player names to IDs
        ids_out = []
        ids_in = []
        
        for name in player_names_out:
            matches = store.find_players_by_name(name, fuzzy=True)
            if not matches:
                return f"Error: Could not find player '{name}' to transfer out."
            if len(matches) > 1 and matches[0][1] < 0.95:
                return f"Error: Ambiguous player name '{name}'. Please be more specific."
            ids_out.append(matches[0][0].id)
        
        for name in player_names_in:
            matches = store.find_players_by_name(name, fuzzy=True)
            if not matches:
                return f"Error: Could not find player '{name}' to transfer in."
            if len(matches) > 1 and matches[0][1] < 0.95:
                return f"Error: Ambiguous player name '{name}'. Please be more specific."
            ids_in.append(matches[0][0].id)
        
        # Get entry ID
        entry_id = store.get_user_entry_id(client)
        if not entry_id:
            return "Error: Could not determine your entry ID."
        
        # Execute transfers
        gw = await client.get_current_gameweek()
        my_team = await client.get_my_team(entry_id)
        current_map = {p['element']: p['selling_price'] for p in my_team['picks']}
        
        all_players = await client.get_players()
        cost_map = {p.id: p.now_cost for p in all_players}
        
        transfers = []
        for i in range(len(ids_out)):
            if ids_out[i] not in current_map:
                player_name = store.get_player_name(ids_out[i])
                return f"Error: You do not own {player_name}"
            transfers.append({
                "element_out": ids_out[i],
                "element_in": ids_in[i],
                "selling_price": current_map[ids_out[i]],
                "purchase_price": cost_map[ids_in[i]]
            })
            
        payload = TransferPayload(entry=entry_id, event=gw, transfers=transfers)
        res = await client.execute_transfers(payload)
        return f"Success: {res}"
    except Exception as e:
        return f"Transfer failed: {str(e)}"

@mcp.tool()
async def get_current_gameweek() -> str:
    """
    Get the current or upcoming gameweek information.
    Returns the gameweek that is currently active (before deadline) or the next gameweek (after deadline).
    Use this to determine which gameweek to plan transfers for.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data or not store.bootstrap_data.events:
        return "Error: Gameweek data not available."
    
    try:
        now = datetime.utcnow()
        
        for event in store.bootstrap_data.events:
            if event.is_current:
                deadline = datetime.fromisoformat(event.deadline_time.replace('Z', '+00:00'))
                if now < deadline:
                    return (
                        f"**Current Gameweek: {event.name}**\n"
                        f"Deadline: {event.deadline_time}\n"
                        f"Status: Active - deadline not yet passed\n"
                        f"Finished: {event.finished}\n"
                        f"Average Score: {event.average_entry_score or 'N/A'}\n"
                        f"Highest Score: {event.highest_score or 'N/A'}"
                    )
                else:
                    break
        
        for event in store.bootstrap_data.events:
            if event.is_next:
                return (
                    f"**Upcoming Gameweek: {event.name}**\n"
                    f"Deadline: {event.deadline_time}\n"
                    f"Status: Next gameweek (current deadline has passed)\n"
                    f"Released: {event.released}\n"
                    f"Can Enter: {event.can_enter}"
                )
        
        for event in store.bootstrap_data.events:
            if not event.finished:
                return (
                    f"**Upcoming Gameweek: {event.name}**\n"
                    f"Deadline: {event.deadline_time}\n"
                    f"Status: Upcoming\n"
                    f"Released: {event.released}"
                )
        
        return "Error: No active or upcoming gameweek found."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_gameweek_info(gameweek_number: int) -> str:
    """
    Get detailed information about a specific gameweek by number (1-38).
    Includes deadline, scores, top players, and statistics.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data or not store.bootstrap_data.events:
        return "Error: Gameweek data not available."
    
    try:
        event = next((e for e in store.bootstrap_data.events if e.id == gameweek_number), None)
        if not event:
            return f"Error: Gameweek {gameweek_number} not found."
        
        output = [
            f"**{event.name}**",
            f"Deadline: {event.deadline_time}",
            f"Status: {'Current' if event.is_current else 'Previous' if event.is_previous else 'Next' if event.is_next else 'Upcoming'}",
            f"Finished: {event.finished}",
            f"Released: {event.released}",
            ""
        ]
        
        if event.finished:
            output.extend([
                "**Statistics:**",
                f"Average Score: {event.average_entry_score}",
                f"Highest Score: {event.highest_score}",
                ""
            ])
            
            if event.top_element_info:
                top_player = store.get_player_name(event.top_element_info.id)
                output.extend([
                    "**Top Performer:**",
                    f"Player: {top_player}",
                    f"Points: {event.top_element_info.points}",
                    ""
                ])
        
        if event.most_captained:
            most_cap = store.get_player_name(event.most_captained)
            most_vc = store.get_player_name(event.most_vice_captained)
            most_sel = store.get_player_name(event.most_selected)
            most_trans = store.get_player_name(event.most_transferred_in)
            
            output.extend([
                "**Popular Choices:**",
                f"Most Captained: {most_cap}",
                f"Most Vice-Captained: {most_vc}",
                f"Most Selected: {most_sel}",
                f"Most Transferred In: {most_trans}",
            ])
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_team_info(team_name: str) -> str:
    """
    Get detailed information about a specific Premier League team by name.
    Includes strength ratings for home/away attack/defence.
    Example: "Arsenal", "Man City", "Liverpool"
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data:
        return "Error: Team data not available."
    
    # Find team by name
    matching_teams = [
        t for t in store.bootstrap_data.teams
        if team_name.lower() in t.name.lower() or team_name.lower() in t.short_name.lower()
    ]
    
    if not matching_teams:
        return f"No team found matching '{team_name}'"
    
    if len(matching_teams) > 1:
        team_list = ", ".join([f"{t.name} ({t.short_name})" for t in matching_teams])
        return f"Multiple teams found: {team_list}. Please be more specific."
    
    team = matching_teams[0]
    team_dict = store.get_team_by_id(team.id)
    
    output = [
        f"**{team_dict['name']} ({team_dict['short_name']})**",
        ""
    ]
    
    if team_dict.get('strength'):
        output.append(f"Overall Strength: {team_dict['strength']}")
    
    if team_dict.get('strength_overall_home') or team_dict.get('strength_overall_away'):
        output.extend([
            "",
            "**Overall Strength:**",
            f"Home: {team_dict.get('strength_overall_home', 'N/A')}",
            f"Away: {team_dict.get('strength_overall_away', 'N/A')}",
        ])
    
    if team_dict.get('strength_attack_home') or team_dict.get('strength_attack_away'):
        output.extend([
            "",
            "**Attack Strength:**",
            f"Home: {team_dict.get('strength_attack_home', 'N/A')}",
            f"Away: {team_dict.get('strength_attack_away', 'N/A')}",
        ])
    
    if team_dict.get('strength_defence_home') or team_dict.get('strength_defence_away'):
        output.extend([
            "",
            "**Defence Strength:**",
            f"Home: {team_dict.get('strength_defence_home', 'N/A')}",
            f"Away: {team_dict.get('strength_defence_away', 'N/A')}",
        ])
    
    return "\n".join(output)

@mcp.tool()
async def list_all_teams() -> str:
    """
    List all Premier League teams with their basic information.
    Useful for finding team names or comparing team strengths.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    teams = store.get_all_teams()
    if not teams:
        return "Error: Team data not available."
    
    output = ["**Premier League Teams:**\n"]
    
    teams_sorted = sorted(teams, key=lambda t: t['name'])
    
    for team in teams_sorted:
        strength_info = ""
        if team.get('strength_overall_home') and team.get('strength_overall_away'):
            avg_strength = (team['strength_overall_home'] + team['strength_overall_away']) / 2
            strength_info = f" | Strength: {avg_strength:.0f}"
        
        output.append(
            f"{team['name']:20s} ({team['short_name']}){strength_info}"
        )
    
    return "\n".join(output)

@mcp.tool()
async def search_players_by_team(team_name: str) -> str:
    """
    Search for all players from a specific team by team name.
    Returns player names, positions, prices, and form.
    Example: "Arsenal", "Liverpool", "Man City"
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data:
        return "Error: Player data not available."
    
    try:
        matching_teams = [
            t for t in store.bootstrap_data.teams
            if team_name.lower() in t.name.lower() or team_name.lower() in t.short_name.lower()
        ]
        
        if not matching_teams:
            return f"No teams found matching '{team_name}'"
        
        if len(matching_teams) > 1:
            team_list = ", ".join([f"{t.name} ({t.short_name})" for t in matching_teams])
            return f"Multiple teams found: {team_list}. Please be more specific."
        
        team = matching_teams[0]
        
        players = [
            p for p in store.bootstrap_data.elements
            if p.team == team.id
        ]
        
        if not players:
            return f"No players found for {team.name}"
        
        position_order = {'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
        players_sorted = sorted(
            players,
            key=lambda p: (position_order.get(p.position or 'ZZZ', 5), -p.now_cost)
        )
        
        output = [f"**{team.name} ({team.short_name}) Squad:**\n"]
        
        current_position = None
        for p in players_sorted:
            if p.position != current_position:
                current_position = p.position
                output.append(f"\n**{current_position}:**")
            
            price = p.now_cost / 10
            news_indicator = " ⚠️" if p.news else ""
            status_indicator = "" if p.status == 'a' else f" [{p.status}]"
            
            output.append(
                f"├─ {p.web_name:20s} | £{price:4.1f}m | "
                f"Form: {p.form:4s} | PPG: {p.points_per_game:4s}{status_indicator}{news_indicator}"
            )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_injury_and_lineup_predictions() -> str:
    """
    Get predicted lineups and injury status for upcoming Premier League matches from RotoWire.
    This is crucial for understanding which players are likely to play and who to avoid.
    Shows OUT, DOUBTFUL, and EXPECTED players with confidence ratings.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        scraper = RotoWireLineupScraper()
        lineup_statuses = await scraper.scrape_premier_league_lineups()
        
        if not lineup_statuses:
            return "No lineup predictions available at this time. RotoWire may not have published lineups yet."
        
        out_players = [s for s in lineup_statuses if s.status == 'OUT']
        doubtful_players = [s for s in lineup_statuses if s.status == 'DOUBTFUL']
        expected_players = [s for s in lineup_statuses if s.status == 'EXPECTED']
        
        output = ["**Premier League Lineup Predictions & Injury Status**\n"]
        
        if out_players:
            output.append(f"**🚫 OUT ({len(out_players)} players):**")
            for player in sorted(out_players, key=lambda x: x.team):
                output.append(
                    f"├─ {player.player_name} ({player.team}) - {player.reason} "
                    f"[Confidence: {player.confidence:.0%}]"
                )
            output.append("")
        
        if doubtful_players:
            output.append(f"**⚠️ DOUBTFUL ({len(doubtful_players)} players):**")
            for player in sorted(doubtful_players, key=lambda x: x.team):
                output.append(
                    f"├─ {player.player_name} ({player.team}) - {player.reason} "
                    f"[Confidence: {player.confidence:.0%}]"
                )
            output.append("")
        
        if expected_players:
            output.append(f"**✅ EXPECTED TO START ({len(expected_players)} key players):**")
            for player in sorted(expected_players, key=lambda x: x.team):
                output.append(
                    f"├─ {player.player_name} ({player.team}) - {player.reason} "
                    f"[Confidence: {player.confidence:.0%}]"
                )
        
        output.append("\n**Note:** This data is scraped from RotoWire and updates as lineups are confirmed.")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching lineup predictions: {str(e)}"

@mcp.tool()
async def get_players_to_avoid() -> str:
    """
    Get a list of players to avoid for transfers based on injury status and lineup predictions.
    Returns players who are OUT or DOUBTFUL with risk levels.
    Use this before making transfers to avoid bringing in injured players.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        scraper = RotoWireLineupScraper()
        lineup_statuses = await scraper.scrape_premier_league_lineups()
        
        if not lineup_statuses:
            return "No lineup data available at this time."
        
        ai_format = scraper.convert_to_ai_format(lineup_statuses)
        players_to_avoid = ai_format['players_to_avoid']
        
        if not players_to_avoid:
            return "✅ No players currently flagged to avoid based on injury/lineup status."
        
        output = [
            f"**⚠️ Players to Avoid ({len(players_to_avoid)} players)**\n",
            "These players are OUT or DOUBTFUL and should be avoided for transfers:\n"
        ]
        
        high_risk = [p for p in players_to_avoid if p['risk_level'] == 'high']
        medium_risk = [p for p in players_to_avoid if p['risk_level'] == 'medium']
        
        if high_risk:
            output.append("**🔴 HIGH RISK (OUT):**")
            for player in high_risk:
                output.append(
                    f"├─ {player['player_name']} - {player['reason']} "
                    f"(Expected points: {player['predicted_points_next_3_gameweeks']:.1f})"
                )
            output.append("")
        
        if medium_risk:
            output.append("**🟡 MEDIUM RISK (DOUBTFUL):**")
            for player in medium_risk:
                output.append(
                    f"├─ {player['player_name']} - {player['reason']} "
                    f"(Expected points: {player['predicted_points_next_3_gameweeks']:.1f})"
                )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching players to avoid: {str(e)}"

@mcp.tool()
async def check_player_availability(player_name: str) -> str:
    """
    Check if a specific player is available to play based on RotoWire lineup predictions.
    Useful before making a transfer to verify the player is not injured or suspended.
    Provide player name (can be partial match).
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        scraper = RotoWireLineupScraper()
        lineup_statuses = await scraper.scrape_premier_league_lineups()
        
        if not lineup_statuses:
            return f"No lineup data available to check {player_name}'s status."
        
        matches = [
            s for s in lineup_statuses
            if player_name.lower() in s.player_name.lower()
        ]
        
        if not matches:
            return f"✅ {player_name} not found in injury/lineup reports. Likely available to play."
        
        if len(matches) > 1:
            output = [f"Found {len(matches)} players matching '{player_name}':\n"]
            for match in matches:
                status_emoji = "🚫" if match.status == "OUT" else "⚠️" if match.status == "DOUBTFUL" else "✅"
                output.append(
                    f"{status_emoji} {match.player_name} ({match.team}) - {match.status}: {match.reason} "
                    f"[Confidence: {match.confidence:.0%}]"
                )
            return "\n".join(output)
        
        player = matches[0]
        status_emoji = "🚫" if player.status == "OUT" else "⚠️" if player.status == "DOUBTFUL" else "✅"
        
        return (
            f"{status_emoji} **{player.player_name} ({player.team})**\n"
            f"Status: {player.status}\n"
            f"Reason: {player.reason}\n"
            f"Confidence: {player.confidence:.0%}\n\n"
            f"{'❌ AVOID - Player is not expected to play' if player.status == 'OUT' else '⚠️ RISKY - Player may not play' if player.status == 'DOUBTFUL' else '✅ AVAILABLE - Player expected to play'}"
        )
    except Exception as e:
        return f"Error checking player availability: {str(e)}"

@mcp.tool()
async def list_all_gameweeks() -> str:
    """
    List all gameweeks with their status (finished, current, upcoming).
    Useful for getting an overview of the season.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data or not store.bootstrap_data.events:
        return "Error: Gameweek data not available."
    
    try:
        output = ["**All Gameweeks:**\n"]
        
        for event in store.bootstrap_data.events:
            status = []
            if event.is_current:
                status.append("CURRENT")
            if event.is_previous:
                status.append("PREVIOUS")
            if event.is_next:
                status.append("NEXT")
            if event.finished:
                status.append("FINISHED")
            
            status_str = f" [{', '.join(status)}]" if status else ""
            avg_score = f" | Avg: {event.average_entry_score}" if event.average_entry_score else ""
            
            output.append(
                f"GW{event.id}: {event.name}{status_str} | "
                f"Deadline: {event.deadline_time[:10]}{avg_score}"
            )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def find_player(player_name: str) -> str:
    """
    Find a player by name with intelligent fuzzy matching.
    Handles variations in spelling, partial names, and common nicknames.
    If multiple players match, returns disambiguation options.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data:
        return "Error: Player data not available."
    
    try:
        matches = store.find_players_by_name(player_name, fuzzy=True)
        
        if not matches:
            return f"No players found matching '{player_name}'. Try a different spelling or use the player's surname."
        
        if len(matches) == 1 or (matches[0][1] >= 0.95 and matches[0][1] - matches[1][1] > 0.2):
            player = matches[0][0]
            return _format_player_details(player)
        
        output = [f"Found {len(matches)} players matching '{player_name}':\n"]
        
        for player, score in matches[:10]:
            price = player.now_cost / 10
            news_indicator = " ⚠️" if player.news else ""
            status_indicator = "" if player.status == 'a' else f" [{player.status}]"
            
            output.append(
                f"├─ {player.first_name} {player.second_name} ({player.web_name}) - "
                f"{player.team_name} {player.position} | £{price:.1f}m | "
                f"Form: {player.form} | PPG: {player.points_per_game}{status_indicator}{news_indicator}"
            )
        
        output.append("\nPlease specify the full name for more details.")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_player_details(player_name: str) -> str:
    """
    Get detailed information about a specific player by name.
    Includes price, form, team, position, and current status.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    matches = store.find_players_by_name(player_name, fuzzy=True)
    
    if not matches:
        return f"No player found matching '{player_name}'"
    
    if len(matches) > 1 and matches[0][1] < 0.95:
        return f"Ambiguous player name. Please use find_player to see all matches for '{player_name}'"
    
    player = matches[0][0]
    return _format_player_details(player)

@mcp.tool()
async def compare_players(player_names: list[str]) -> str:
    """
    Compare multiple players side-by-side using their names.
    Provide a list of 2-5 player names to compare their stats, prices, and form.
    Useful for transfer decisions.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data:
        return "Error: Player data not available."
    
    if len(player_names) < 2:
        return "Error: Please provide at least 2 player names to compare."
    
    if len(player_names) > 5:
        return "Error: Maximum 5 players can be compared at once."
    
    try:
        players_to_compare = []
        ambiguous = []
        
        for name in player_names:
            matches = store.find_players_by_name(name, fuzzy=True)
            
            if not matches:
                return f"Error: No player found matching '{name}'"
            
            if len(matches) == 1 or (matches[0][1] >= 0.95 and len(matches) > 1 and matches[0][1] - matches[1][1] > 0.2):
                players_to_compare.append(matches[0][0])
            else:
                ambiguous.append((name, matches[:3]))
        
        if ambiguous:
            output = ["Cannot compare - ambiguous player names:\n"]
            for name, matches in ambiguous:
                output.append(f"\n'{name}' could be:")
                for player, score in matches:
                    output.append(f"  - {player.first_name} {player.second_name} ({player.team_name})")
            output.append("\nPlease use more specific names or full names.")
            return "\n".join(output)
        
        output = [f"**Player Comparison ({len(players_to_compare)} players)**\n"]
        output.append("=" * 80)
        
        for player in players_to_compare:
            price = player.now_cost / 10
            news_indicator = " ⚠️" if player.news else ""
            status_indicator = "" if player.status == 'a' else f" [{player.status}]"
            
            output.extend([
                f"\n**{player.web_name}** ({player.first_name} {player.second_name})",
                f"├─ Team: {player.team_name} | Position: {player.position}",
                f"├─ Price: £{price:.1f}m",
                f"├─ Form: {player.form} | Points per Game: {player.points_per_game}",
                f"├─ Total Points: {getattr(player, 'total_points', 'N/A')}",
                f"├─ Status: {player.status}{status_indicator}{news_indicator}",
            ])
            
            if player.news:
                output.append(f"├─ News: {player.news}")
            
            if hasattr(player, 'selected_by_percent'):
                output.append(f"├─ Selected by: {getattr(player, 'selected_by_percent', 'N/A')}%")
            
            if hasattr(player, 'minutes'):
                output.append(f"├─ Minutes played: {getattr(player, 'minutes', 'N/A')}")
            
            output.append("=" * 80)
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

def _format_player_details(player: 'ElementData') -> str:
    """Helper function to format detailed player information"""
    price = player.now_cost / 10
    news_indicator = " ⚠️" if player.news else ""
    status_indicator = "" if player.status == 'a' else f" [{player.status}]"
    
    output = [
        f"**{player.web_name}** ({player.first_name} {player.second_name})",
        f"Team: {player.team_name}",
        f"Position: {player.position}",
        f"Price: £{price:.1f}m",
        "",
        "**Performance:**",
        f"├─ Form: {player.form}",
        f"├─ Points per Game: {player.points_per_game}",
        f"├─ Total Points: {getattr(player, 'total_points', 'N/A')}",
        f"├─ Minutes: {getattr(player, 'minutes', 'N/A')}",
        "",
        f"**Status:** {player.status}{status_indicator}{news_indicator}",
    ]
    
    if player.news:
        output.extend([
            "",
            f"**News:** {player.news}"
        ])
    
    if hasattr(player, 'selected_by_percent'):
        output.extend([
            "",
            "**Popularity:**",
            f"├─ Selected by: {getattr(player, 'selected_by_percent', 'N/A')}%",
            f"├─ Transfers in (GW): {getattr(player, 'transfers_in_event', 'N/A')}",
            f"├─ Transfers out (GW): {getattr(player, 'transfers_out_event', 'N/A')}",
        ])
    
    if hasattr(player, 'goals_scored'):
        output.extend([
            "",
            "**Stats:**",
            f"├─ Goals: {getattr(player, 'goals_scored', 0)}",
            f"├─ Assists: {getattr(player, 'assists', 0)}",
            f"├─ Clean Sheets: {getattr(player, 'clean_sheets', 0)}",
            f"├─ Bonus Points: {getattr(player, 'bonus', 0)}",
        ])
    
    return "\n".join(output)

@mcp.tool()
async def get_player_summary(player_name: str) -> str:
    """
    Get comprehensive player summary including upcoming fixtures, gameweek history, and past season performance.
    Provide the player's name to get detailed stats, fixture difficulty, and historical performance.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        # Find player by name
        matches = store.find_players_by_name(player_name, fuzzy=True)
        if not matches:
            return f"No player found matching '{player_name}'"
        
        if len(matches) > 1 and matches[0][1] < 0.95:
            return f"Ambiguous player name. Please use find_player to see all matches for '{player_name}'"
        
        player = matches[0][0]
        player_id = player.id
        
        # Fetch detailed summary from API
        summary_data = await client.get_element_summary(player_id)
        
        # Enrich history and fixtures with team names
        history = summary_data.get('history', [])
        history = store.enrich_gameweek_history(history)
        
        fixtures = summary_data.get('fixtures', [])
        fixtures = store.enrich_fixtures(fixtures)
        
        output = [
            f"**{player.web_name}** ({player.first_name} {player.second_name})",
            f"Team: {player.team_name} | Position: {player.position} | Price: £{player.now_cost/10:.1f}m",
            "",
        ]
        
        # Upcoming Fixtures
        if fixtures:
            output.append(f"**Upcoming Fixtures ({len(fixtures)}):**")
            for fixture in fixtures[:5]:
                opponent_name = fixture.get('team_h_short') if not fixture['is_home'] else fixture.get('team_a_short', 'Unknown')
                home_away = "H" if fixture['is_home'] else "A"
                difficulty = "●" * fixture['difficulty']
                
                output.append(
                    f"├─ GW{fixture['event']}: vs {opponent_name} ({home_away}) | "
                    f"Difficulty: {difficulty} ({fixture['difficulty']}/5)"
                )
            output.append("")
        
        # Recent Gameweek History
        if history:
            recent_history = history[-5:]
            output.append(f"**Recent Performance (Last {len(recent_history)} GWs):**")
            
            for gw in recent_history:
                opponent_name = gw.get('opponent_team_short', 'Unknown')
                home_away = "H" if gw['was_home'] else "A"
                
                output.append(
                    f"├─ GW{gw['round']}: {gw['total_points']}pts vs {opponent_name} ({home_away}) | "
                    f"{gw['minutes']}min | G:{gw['goals_scored']} A:{gw['assists']} "
                    f"CS:{gw['clean_sheets']} | Bonus: {gw['bonus']}"
                )
            
            total_points = sum(gw['total_points'] for gw in recent_history)
            avg_points = total_points / len(recent_history)
            total_minutes = sum(gw['minutes'] for gw in recent_history)
            avg_minutes = total_minutes / len(recent_history)
            
            output.extend([
                "",
                f"**Recent Averages:**",
                f"├─ Points per game: {avg_points:.1f}",
                f"├─ Minutes per game: {avg_minutes:.0f}",
                ""
            ])
        
        # Past Season Performance
        history_past = summary_data.get('history_past', [])
        if history_past:
            output.append(f"**Past Seasons ({len(history_past)} seasons):**")
            for season in history_past[-3:]:
                output.append(
                    f"├─ {season['season_name']}: {season['total_points']}pts | "
                    f"{season['minutes']}min | G:{season['goals_scored']} A:{season['assists']} | "
                    f"£{season['start_cost']/10:.1f}m → £{season['end_cost']/10:.1f}m"
                )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching player summary: {str(e)}"
@mcp.tool()
async def analyze_squad_recent_performance(num_gameweeks: int = 5) -> str:
    """
    Analyze recent gameweek performance for all players in your current squad.
    Shows detailed stats from the last N gameweeks to identify underperforming players
    who might be candidates for transfer, and inform players who are performing well.
    
    Args:
        num_gameweeks: Number of recent gameweeks to analyze (default: 5)
    
    Returns:
        Detailed analysis of each squad player's recent form with transfer recommendations
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        entry_id = store.get_user_entry_id(client)
        if not entry_id:
            return "Error: Could not determine your entry ID."
        
        # Get current squad
        my_team = await client.get_my_team(entry_id)
        picks = my_team['picks']
        
        # Get all players for price info
        all_players = await client.get_players()
        p_map = {p.id: p for p in all_players}
        
        output = [
            f"**Squad Performance Analysis (Last {num_gameweeks} Gameweeks)**\n",
            f"Bank: £{my_team['transfers']['bank']/10:.1f}m\n"
        ]
        
        # Analyze each player
        player_analyses = []
        
        for pick in picks:
            element_id = pick['element']
            player = p_map.get(element_id)
            if not player:
                continue
            
            # Fetch detailed player summary
            try:
                summary = await client.get_element_summary(element_id)
                history = summary.get('history', [])
                
                # Enrich history with team names
                history = store.enrich_gameweek_history(history)
                
                if not history:
                    player_analyses.append({
                        'player': player,
                        'pick': pick,
                        'avg_points': 0,
                        'avg_minutes': 0,
                        'total_points': 0,
                        'games_played': 0,
                        'recent_form': 'No data'
                    })
                    continue
                
                # Get last N gameweeks
                recent_gws = history[-num_gameweeks:]
                
                # Calculate stats
                total_points = sum(gw['total_points'] for gw in recent_gws)
                total_minutes = sum(gw['minutes'] for gw in recent_gws)
                games_played = len([gw for gw in recent_gws if gw['minutes'] > 0])
                avg_points = total_points / len(recent_gws) if recent_gws else 0
                avg_minutes = total_minutes / len(recent_gws) if recent_gws else 0
                
                # Calculate recent form trend (last 3 vs previous games)
                if len(recent_gws) >= 3:
                    last_3 = recent_gws[-3:]
                    prev_games = recent_gws[:-3] if len(recent_gws) > 3 else []
                    
                    last_3_avg = sum(gw['total_points'] for gw in last_3) / 3
                    prev_avg = sum(gw['total_points'] for gw in prev_games) / len(prev_games) if prev_games else last_3_avg
                    
                    if last_3_avg > prev_avg * 1.2:
                        form_trend = "📈 Improving"
                    elif last_3_avg < prev_avg * 0.8:
                        form_trend = "📉 Declining"
                    else:
                        form_trend = "➡️ Stable"
                else:
                    form_trend = "➡️ Stable"
                
                # Calculate transfer trends from recent gameweeks
                recent_transfers_balance = sum(gw.get('transfers_balance', 0) for gw in recent_gws)
                last_gw_transfers = recent_gws[-1].get('transfers_balance', 0) if recent_gws else 0
                
                # Determine transfer sentiment
                if recent_transfers_balance < -100000:
                    transfer_sentiment = "🔴 Heavy selling"
                elif recent_transfers_balance < -50000:
                    transfer_sentiment = "🟠 Moderate selling"
                elif recent_transfers_balance < -10000:
                    transfer_sentiment = "🟡 Light selling"
                elif recent_transfers_balance > 100000:
                    transfer_sentiment = "🟢 Heavy buying"
                elif recent_transfers_balance > 50000:
                    transfer_sentiment = "🟢 Moderate buying"
                elif recent_transfers_balance > 10000:
                    transfer_sentiment = "🟢 Light buying"
                else:
                    transfer_sentiment = "⚪ Stable"
                
                player_analyses.append({
                    'player': player,
                    'pick': pick,
                    'avg_points': avg_points,
                    'avg_minutes': avg_minutes,
                    'total_points': total_points,
                    'games_played': games_played,
                    'recent_form': form_trend,
                    'recent_gws': recent_gws,
                    'transfers_balance': recent_transfers_balance,
                    'last_gw_transfers': last_gw_transfers,
                    'transfer_sentiment': transfer_sentiment
                })
                
            except Exception as e:
                logger.error(f"Error fetching summary for player {element_id}: {e}")
                continue
        
        # Sort by average points (ascending to show worst performers first)
        player_analyses.sort(key=lambda x: x['avg_points'])
        
        # Categorize players
        underperformers = []
        solid_performers = []
        star_performers = []
        
        for analysis in player_analyses:
            avg_pts = analysis['avg_points']
            if avg_pts < 2.5:
                underperformers.append(analysis)
            elif avg_pts < 5:
                solid_performers.append(analysis)
            else:
                star_performers.append(analysis)
        
        # Output underperformers (transfer candidates)
        if underperformers:
            output.append(f"**🚨 UNDERPERFORMERS - Transfer Candidates ({len(underperformers)} players)**\n")
            for analysis in underperformers:
                player = analysis['player']
                pick = analysis['pick']
                role = " (C)" if pick['is_captain'] else " (VC)" if pick['is_vice_captain'] else ""
                bench = " [BENCH]" if pick['position'] > 11 else ""
                
                # Get last gameweek info
                last_gw = analysis['recent_gws'][-1] if analysis.get('recent_gws') else None
                last_gw_str = ""
                if last_gw:
                    opp_name = last_gw.get('opponent_team_short', f"Team {last_gw.get('opponent_team', '?')}")
                    ha = "H" if last_gw['was_home'] else "A"
                    last_gw_str = f" | Last GW: {last_gw['total_points']}pts, {last_gw['minutes']}min vs {opp_name}({ha})"
                    
                    # Add warning if didn't play last game
                    if last_gw['minutes'] == 0:
                        last_gw_str += " ⚠️ DNP"
                
                # Format transfer balance
                transfers_str = f"{analysis['transfers_balance']:+,}" if analysis['transfers_balance'] != 0 else "0"
                
                output.extend([
                    f"\n**{player.web_name}** ({player.team_name} {player.position}) £{pick['selling_price']/10:.1f}m{role}{bench}",
                    f"├─ Recent Form: {analysis['recent_form']}{last_gw_str}",
                    f"├─ Avg Points/Game: {analysis['avg_points']:.1f} (Last {num_gameweeks} GWs)",
                    f"├─ Total Points: {analysis['total_points']} in {analysis['games_played']} games",
                    f"├─ Avg Minutes: {analysis['avg_minutes']:.0f}/90",
                    f"├─ Community Sentiment: {analysis['transfer_sentiment']} ({transfers_str} net transfers)",
                ])
                
                # Show last 3 gameweeks detail
                if analysis.get('recent_gws'):
                    last_3 = analysis['recent_gws'][-3:]
                    gw_details = []
                    for gw in last_3:
                        opp_name = gw.get('opponent_team_short', f"Team {gw.get('opponent_team', '?')}")
                        ha = "H" if gw['was_home'] else "A"
                        mins_str = f", {gw['minutes']}min" if gw['minutes'] < 90 else ""
                        gw_details.append(f"GW{gw['round']}: {gw['total_points']}pts{mins_str} vs {opp_name}({ha})")
                    output.append(f"├─ Last 3 GWs: {' | '.join(gw_details)}")
                
                # Add recommendation with last game context and transfer sentiment
                recommendations = []
                
                if last_gw and last_gw['minutes'] == 0:
                    recommendations.append("Did not play last game - check injury/rotation status urgently")
                elif analysis['avg_minutes'] < 60:
                    recommendations.append("Low minutes - consider transferring out")
                elif analysis['avg_points'] < 2:
                    recommendations.append("Poor returns - strong transfer candidate")
                else:
                    recommendations.append("Underperforming - monitor closely")
                
                # Add transfer sentiment context
                if analysis['transfers_balance'] < -50000:
                    recommendations.append(f"Community is heavily selling ({analysis['transfers_balance']:,} net)")
                elif analysis['transfers_balance'] < -10000:
                    recommendations.append(f"Community losing confidence ({analysis['transfers_balance']:,} net)")
                
                rec_icon = "🚨" if (last_gw and last_gw['minutes'] == 0) or analysis['transfers_balance'] < -50000 else "⚠️"
                output.append(f"└─ {rec_icon} **RECOMMENDATION**: {' | '.join(recommendations)}")
        
        # Output solid performers
        if solid_performers:
            output.append(f"\n\n**✅ SOLID PERFORMERS - Keep ({len(solid_performers)} players)**\n")
            for analysis in solid_performers:
                player = analysis['player']
                pick = analysis['pick']
                role = " (C)" if pick['is_captain'] else " (VC)" if pick['is_vice_captain'] else ""
                
                # Get last game info
                last_gw = analysis['recent_gws'][-1] if analysis.get('recent_gws') else None
                last_gw_str = ""
                if last_gw:
                    last_gw_str = f" | Last: {last_gw['total_points']}pts"
                    if last_gw['minutes'] == 0:
                        last_gw_str += " ⚠️ DNP"
                    elif last_gw['minutes'] < 60:
                        last_gw_str += f" ({last_gw['minutes']}min)"
                
                # Add transfer sentiment if significant
                sentiment_str = ""
                if abs(analysis['transfers_balance']) > 10000:
                    sentiment_str = f" | {analysis['transfer_sentiment']}"
                
                output.append(
                    f"├─ {player.web_name} ({player.team_name} {player.position}): "
                    f"{analysis['avg_points']:.1f} pts/game | {analysis['recent_form']}{last_gw_str}{sentiment_str}"
                )
        
        # Output star performers
        if star_performers:
            output.append(f"\n\n**⭐ STAR PERFORMERS - Essential ({len(star_performers)} players)**\n")
            for analysis in star_performers:
                player = analysis['player']
                pick = analysis['pick']
                role = " (C)" if pick['is_captain'] else " (VC)" if pick['is_vice_captain'] else ""
                
                # Get last game info
                last_gw = analysis['recent_gws'][-1] if analysis.get('recent_gws') else None
                last_gw_str = ""
                if last_gw:
                    last_gw_str = f" | Last: {last_gw['total_points']}pts"
                    if last_gw['minutes'] == 0:
                        last_gw_str += " ⚠️ DNP"
                    elif last_gw['minutes'] < 60:
                        last_gw_str += f" ({last_gw['minutes']}min)"
                
                # Add transfer sentiment if significant
                sentiment_str = ""
                if abs(analysis['transfers_balance']) > 10000:
                    sentiment_str = f" | {analysis['transfer_sentiment']}"
                
                output.append(
                    f"├─ {player.web_name} ({player.team_name} {player.position}): "
                    f"{analysis['avg_points']:.1f} pts/game | {analysis['recent_form']}{last_gw_str}{sentiment_str}{role}"
                )
        
        # Summary recommendations
        output.extend([
            "\n\n**📊 SUMMARY**",
            f"├─ Underperformers: {len(underperformers)} players averaging <2.5 pts/game",
            f"├─ Solid Performers: {len(solid_performers)} players averaging 2.5-5 pts/game",
            f"├─ Star Performers: {len(star_performers)} players averaging >5 pts/game",
        ])
        
        if underperformers:
            output.append(f"\n**💡 TRANSFER PRIORITY**: Focus on replacing {underperformers[0]['player'].web_name} first")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error analyzing squad performance: {str(e)}"


@mcp.tool()
async def get_my_performance() -> str:
    """
    Get your FPL performance including overall rank, gameweek rank, points, and league standings.
    Use this to check how you're doing in FPL.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        entry_id = store.get_user_entry_id(client)
        if not entry_id:
            return "Error: Could not determine your entry ID."
        
        entry_data = await client.get_manager_entry(entry_id)
        
        output = [
            f"**{entry_data['name']}**",
            f"Manager: {entry_data['player_first_name']} {entry_data['player_last_name']}",
            f"Region: {entry_data['player_region_name']} ({entry_data['player_region_iso_code_short']})",
            f"Years Active: {entry_data['years_active']}",
            "",
            "**Current Season Performance:**",
            f"├─ Overall Points: {entry_data['summary_overall_points']:,}",
            f"├─ Overall Rank: {entry_data['summary_overall_rank']:,}",
            f"├─ Gameweek {entry_data['current_event']} Points: {entry_data['summary_event_points']}",
            f"├─ Gameweek {entry_data['current_event']} Rank: {entry_data['summary_event_rank']:,}",
            "",
            "**Team Value:**",
            f"├─ Squad Value: £{entry_data['last_deadline_value']/10:.1f}m",
            f"├─ Bank: £{entry_data['last_deadline_bank']/10:.1f}m",
            f"├─ Total Transfers: {entry_data['last_deadline_total_transfers']}",
            "",
        ]
        
        leagues = entry_data.get('leagues', {})
        classic_leagues = leagues.get('classic', [])
        
        if classic_leagues:
            output.append(f"**Leagues ({len(classic_leagues)}):**")
            
            overall_league = next((l for l in classic_leagues if l['name'] == 'Overall'), None)
            if overall_league:
                output.extend([
                    f"\n**Overall League:**",
                    f"├─ Rank: {overall_league['entry_rank']:,} / {overall_league['rank_count']:,}",
                    f"├─ Percentile: Top {overall_league['entry_percentile_rank']}%",
                ])
            
            other_leagues = [l for l in classic_leagues if l['name'] != 'Overall' and l['league_type'] == 'x']
            if other_leagues:
                output.append(f"\n**Private Leagues (Top 5):**")
                sorted_leagues = sorted(other_leagues, key=lambda x: x['entry_rank'])[:5]
                
                for league in sorted_leagues:
                    output.append(
                        f"├─ {league['name']}: "
                        f"Rank {league['entry_rank']}/{league['rank_count']} "
                        f"(Top {league['entry_percentile_rank']}%)"
                    )
        
        cup = leagues.get('cup', {})
        cup_status = cup.get('status', {})
        if cup_status.get('qualification_state'):
            output.extend([
                "",
                "**Cup Status:**",
                f"├─ Qualification: {cup_status['qualification_state']}",
            ])
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching your performance: {str(e)}"

@mcp.tool()
async def get_league_standings(league_name: str, page: int = 1) -> str:
    """
    Get standings for a specific FPL league by name.
    Shows manager rankings, points, and team names within the league.
    Use this to see how managers are performing in one of your leagues.
    Example: "Greatest Fantasy Footy", "Work League"
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        # Find league by name
        league_info = await store.find_league_by_name(client, league_name)
        if not league_info:
            return f"Could not find a league named '{league_name}' in your leagues. Use get_my_info to see your leagues."
        
        league_id = league_info['id']
        
        # Fetch league standings from API
        standings_data = await client.get_league_standings(
            league_id=league_id,
            page_standings=page
        )
        
        league_data = standings_data.get('league', {})
        standings = standings_data.get('standings', {})
        results = standings.get('results', [])
        
        if not results:
            return f"No standings found for league '{league_name}'"
        
        output = [
            f"**{league_data.get('name', league_name)}**",
            f"Total Entries: {standings.get('has_next', False) and 'Many' or len(results)}",
            f"Page: {page}",
            "",
            "**Standings:**",
            ""
        ]
        
        for entry in results:
            rank_change = entry['rank'] - entry['last_rank']
            rank_indicator = "↑" if rank_change < 0 else "↓" if rank_change > 0 else "="
            
            output.append(
                f"{entry['rank']:3d}. {rank_indicator} {entry['entry_name']:30s} | "
                f"{entry['player_name']:20s} | "
                f"GW: {entry['event_total']:3d} | Total: {entry['total']:4d}"
            )
        
        if standings.get('has_next'):
            output.append(f"\n📄 More entries available. Use page={page + 1} to see next page.")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching league standings: {str(e)}"

@mcp.tool()
async def get_manager_gameweek_team(manager_name: str, league_name: str, gameweek: int) -> str:
    """
    Get a manager's team selection for a specific gameweek by their name.
    Shows the 15 players picked, captain/vice-captain, formation, and points scored.
    Provide the manager's name (or team name), the league they're in, and gameweek number.
    Example: manager_name="Jaakko", league_name="Greatest Fantasy Footy", gameweek=13
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    try:
        # Find league first
        league_info = await store.find_league_by_name(client, league_name)
        if not league_info:
            return f"Could not find league '{league_name}'. Use get_my_info to see your leagues."
        
        # Find manager in league
        manager_info = await store.find_manager_by_name(client, league_info['id'], manager_name)
        if not manager_info:
            return f"Could not find manager '{manager_name}' in league '{league_name}'"
        
        manager_team_id = manager_info['entry']
        
        # Fetch gameweek picks from API
        picks_data = await client.get_manager_gameweek_picks(manager_team_id, gameweek)
        
        picks = picks_data.get('picks', [])
        entry_history = picks_data.get('entry_history', {})
        auto_subs = picks_data.get('automatic_subs', [])
        
        if not picks:
            return f"No team data found for {manager_info['player_name']} in gameweek {gameweek}"
        
        # Rehydrate player names
        element_ids = [pick['element'] for pick in picks]
        players_info = store.rehydrate_player_names(element_ids)
        
        output = [
            f"**{manager_info['entry_name']}** - {manager_info['player_name']}",
            f"Gameweek {gameweek}",
            f"Points: {entry_history.get('points', 0)} | Total: {entry_history.get('total_points', 0)}",
            f"Overall Rank: {entry_history.get('overall_rank', 'N/A'):,}",
            f"Team Value: £{entry_history.get('value', 0)/10:.1f}m | Bank: £{entry_history.get('bank', 0)/10:.1f}m",
            f"Transfers: {entry_history.get('event_transfers', 0)} (Cost: {entry_history.get('event_transfers_cost', 0)}pts)",
            f"Points on Bench: {entry_history.get('points_on_bench', 0)}",
            ""
        ]
        
        if picks_data.get('active_chip'):
            output.append(f"**Active Chip:** {picks_data['active_chip']}")
            output.append("")
        
        starting_xi = [p for p in picks if p['position'] <= 11]
        bench = [p for p in picks if p['position'] > 11]
        
        output.append("**Starting XI:**")
        for pick in starting_xi:
            player = players_info.get(pick['element'], {})
            role = " (C)" if pick['is_captain'] else " (VC)" if pick['is_vice_captain'] else ""
            multiplier = f" x{pick['multiplier']}" if pick['multiplier'] > 1 else ""
            
            output.append(
                f"{pick['position']:2d}. {player.get('web_name', 'Unknown'):15s} "
                f"({player.get('team', 'UNK'):3s} {player.get('position', 'UNK')}) | "
                f"£{player.get('price', 0):.1f}m{role}{multiplier}"
            )
        
        output.append("\n**Bench:**")
        for pick in bench:
            player = players_info.get(pick['element'], {})
            output.append(
                f"{pick['position']:2d}. {player.get('web_name', 'Unknown'):15s} "
                f"({player.get('team', 'UNK'):3s} {player.get('position', 'UNK')}) | "
                f"£{player.get('price', 0):.1f}m"
            )
        
        if auto_subs:
            output.append("\n**Automatic Substitutions:**")
            for sub in auto_subs:
                player_out = store.get_player_name(sub['element_out'])
                player_in = store.get_player_name(sub['element_in'])
                output.append(f"├─ {player_out} → {player_in}")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching manager's gameweek team: {str(e)}"

@mcp.tool()
async def compare_managers(manager_names: list[str], league_name: str, gameweek: int) -> str:
    """
    Compare multiple managers' teams for a specific gameweek side-by-side using their names.
    Shows differences in player selection, captaincy choices, and points scored.
    Provide 2-4 manager names (or team names), the league they're in, and gameweek number.
    Example: manager_names=["Jaakko", "Lewis"], league_name="Greatest Fantasy Footy", gameweek=13
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if len(manager_names) < 2:
        return "Error: Please provide at least 2 manager names to compare."
    
    if len(manager_names) > 4:
        return "Error: Maximum 4 managers can be compared at once."
    
    try:
        # Find league first
        league_info = await store.find_league_by_name(client, league_name)
        if not league_info:
            return f"Could not find league '{league_name}'"
        
        # Find all managers
        manager_ids = []
        manager_infos = []
        for name in manager_names:
            manager_info = await store.find_manager_by_name(client, league_info['id'], name)
            if not manager_info:
                return f"Could not find manager '{name}' in league '{league_name}'"
            manager_ids.append(manager_info['entry'])
            manager_infos.append(manager_info)
        
        # Fetch all teams
        teams_data = []
        for team_id in manager_ids:
            picks_data = await client.get_manager_gameweek_picks(team_id, gameweek)
            teams_data.append((team_id, picks_data))
        
        output = [f"**Manager Comparison - Gameweek {gameweek}**\n"]
        
        # Summary comparison
        output.append("**Performance Summary:**")
        for i, (team_id, data) in enumerate(teams_data):
            entry_history = data.get('entry_history', {})
            manager_info = manager_infos[i]
            output.append(
                f"├─ {manager_info['player_name']} ({manager_info['entry_name']}): "
                f"{entry_history.get('points', 0)}pts | "
                f"Rank: {entry_history.get('overall_rank', 'N/A'):,} | "
                f"Transfers: {entry_history.get('event_transfers', 0)} "
                f"(-{entry_history.get('event_transfers_cost', 0)}pts)"
            )
        
        output.append("\n**Captain Choices:**")
        for i, (team_id, data) in enumerate(teams_data):
            picks = data.get('picks', [])
            captain_pick = next((p for p in picks if p['is_captain']), None)
            if captain_pick:
                captain_name = store.get_player_name(captain_pick['element'])
                multiplier = captain_pick.get('multiplier', 2)
                manager_info = manager_infos[i]
                output.append(f"├─ {manager_info['player_name']}: {captain_name} (x{multiplier})")
        
        # Find common and unique players
        all_players = {}
        for i, (team_id, data) in enumerate(teams_data):
            picks = data.get('picks', [])
            starting_xi = [p['element'] for p in picks if p['position'] <= 11]
            all_players[team_id] = set(starting_xi)
        
        common_players = set.intersection(*all_players.values()) if len(all_players) > 1 else set()
        
        if common_players:
            output.append(f"\n**Common Players ({len(common_players)}):**")
            for element_id in list(common_players)[:10]:
                player_name = store.get_player_name(element_id)
                output.append(f"├─ {player_name}")
        
        # Unique players per team
        output.append("\n**Unique Selections:**")
        for i, team_id in enumerate(manager_ids):
            other_teams = [t for t in manager_ids if t != team_id]
            other_players = set()
            for other_id in other_teams:
                other_players.update(all_players.get(other_id, set()))
            
            unique = all_players[team_id] - other_players
            if unique:
                manager_info = manager_infos[i]
                output.append(f"\n{manager_info['player_name']} only:")
                for element_id in list(unique)[:5]:
                    player_name = store.get_player_name(element_id)
                    output.append(f"├─ {player_name}")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error comparing managers: {str(e)}"

@mcp.tool()
async def get_fixtures_for_gameweek(gameweek: int) -> str:
    """
    Get all fixtures for a specific gameweek with team names and kickoff times.
    Useful for planning transfers and understanding fixture difficulty.
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.fixtures_data:
        return "Error: Fixtures data not available."
    
    try:
        gw_fixtures = [f for f in store.fixtures_data if f.event == gameweek]
        
        if not gw_fixtures:
            return f"No fixtures found for gameweek {gameweek}"
        
        # Enrich fixtures with team names
        gw_fixtures_enriched = store.enrich_fixtures(gw_fixtures)
        
        output = [
            f"**Gameweek {gameweek} Fixtures ({len(gw_fixtures_enriched)} matches)**\n"
        ]
        
        gw_fixtures_sorted = sorted(gw_fixtures_enriched, key=lambda x: x.get('kickoff_time') or "")
        
        for fixture in gw_fixtures_sorted:
            home_name = fixture.get('team_h_short', 'Unknown')
            away_name = fixture.get('team_a_short', 'Unknown')
            
            status = "✓" if fixture.get('finished') else "○"
            score = f"{fixture.get('team_h_score')}-{fixture.get('team_a_score')}" if fixture.get('finished') else "vs"
            kickoff = fixture.get('kickoff_time', '')[:16] if fixture.get('kickoff_time') else "TBD"
            
            output.append(
                f"{status} {home_name} {score} {away_name} | "
                f"Kickoff: {kickoff} | "
                f"Difficulty: H:{fixture.get('team_h_difficulty')} A:{fixture.get('team_a_difficulty')}"
            )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching fixtures: {str(e)}"

@mcp.tool()
async def analyze_team_fixtures(team_name: str, num_gameweeks: int = 5) -> str:
    """
    Analyze upcoming fixtures for a specific team to assess difficulty.
    Shows next N gameweeks with opponent strength and home/away status.
    Useful for identifying good times to bring in or sell team assets.
    Provide team name and number of gameweeks to analyze (default: 5).
    """
    client = _get_client()
    if not client: return "Error: Not authenticated. Please use login_to_fpl first."
    
    if not store.bootstrap_data or not store.fixtures_data:
        return "Error: Team or fixtures data not available."
    
    try:
        matching_teams = [
            t for t in store.bootstrap_data.teams
            if team_name.lower() in t.name.lower() or team_name.lower() in t.short_name.lower()
        ]
        
        if not matching_teams:
            return f"No team found matching '{team_name}'"
        
        if len(matching_teams) > 1:
            team_list = ", ".join([f"{t.name} ({t.short_name})" for t in matching_teams])
            return f"Multiple teams found: {team_list}. Please be more specific."
        
        team = matching_teams[0]
        
        current_gw = store.get_current_gameweek()
        if not current_gw:
            return "Error: Could not determine current gameweek"
        
        start_gw = current_gw.id
        end_gw = start_gw + num_gameweeks
        
        team_fixtures = [
            f for f in store.fixtures_data
            if (f.team_h == team.id or f.team_a == team.id)
            and f.event and start_gw <= f.event < end_gw
            and not f.finished
        ]
        
        if not team_fixtures:
            return f"No upcoming fixtures found for {team.name}"
        
        # Enrich fixtures with team names
        team_fixtures_enriched = store.enrich_fixtures(team_fixtures)
        team_fixtures_sorted = sorted(team_fixtures_enriched, key=lambda x: x.get('event') or 999)
        
        output = [
            f"**{team.name} ({team.short_name}) - Next {len(team_fixtures_sorted)} Fixtures**\n"
        ]
        
        total_difficulty = 0
        for fixture in team_fixtures_sorted:
            is_home = fixture.get('team_h') == team.id
            opponent_name = fixture.get('team_a_name') if is_home else fixture.get('team_h_name', 'Unknown')
            
            difficulty = fixture.get('team_h_difficulty') if is_home else fixture.get('team_a_difficulty')
            total_difficulty += difficulty
            
            difficulty_str = "●" * difficulty + "○" * (5 - difficulty)
            home_away = "H" if is_home else "A"
            kickoff = fixture.get('kickoff_time', '')[:10] if fixture.get('kickoff_time') else "TBD"
            
            output.append(
                f"GW{fixture.get('event')}: vs {opponent_name:20s} ({home_away}) | "
                f"{difficulty_str} ({difficulty}/5) | {kickoff}"
            )
        
        avg_difficulty = total_difficulty / len(team_fixtures_sorted)
        output.extend([
            "",
            f"**Average Difficulty:** {avg_difficulty:.1f}/5",
            f"**Assessment:** {'Favorable' if avg_difficulty < 3 else 'Moderate' if avg_difficulty < 3.5 else 'Difficult'} run of fixtures"
        ])
        
        return "\n".join(output)
    except Exception as e:
        return f"Error analyzing fixtures: {str(e)}"