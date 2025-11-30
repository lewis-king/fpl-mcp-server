import uuid
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from .state import store
from .models import TransferPayload
from .rotowire_scraper import RotoWireLineupScraper

# Define the server
mcp = FastMCP("FPL Manager")
BASE_URL = "http://localhost:8000"

@mcp.tool()
async def login_to_fpl() -> str:
    """
    Step 1: Generates a secure login link. 
    Call this when the user wants to log in or when other tools return 'Authentication required'.
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
    Returns a SESSION_ID on success.
    """
    req = store.pending_logins.get(request_id)
    if not req:
        return "Error: Invalid Request ID"
    
    if req.status == "pending":
        return "Login pending. Waiting for user..."
    if req.status == "failed":
        return f"Login failed: {req.error}"
        
    return f"Authentication Successful. Session ID: {req.session_id}"

@mcp.tool()
async def get_my_squad(session_id: str) -> str:
    """Get current team squad and bank balance. Requires Session ID."""
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        my_team = await client.get_my_team(client.team_id)
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
async def search_players(session_id: str, name_query: str) -> str:
    """Search for players by name. Returns price, form, and ID. Requires Session ID."""
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID."
    
    players = await client.get_players()
    matches = [p for p in players if name_query.lower() in p.web_name.lower()]
    
    if not matches: return "No players found."
    
    return "\n".join([f"ID:{p.id} | {p.web_name} ({p.team_name}) | £{p.price}m | Form: {p.form}" for p in matches[:10]])

@mcp.tool()
async def get_top_players(session_id: str) -> str:
    """
    Get top performing players by position (GKP, DEF, MID, FWD) based on points per game.
    Returns top 3 goalkeepers and top 10 for each outfield position.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        top_players = await client.get_top_players_by_position()
        
        output = ["**Top Players by Position (Points per Game)**\n"]
        
        # Format each position
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
async def make_transfers(session_id: str, ids_out: list[int], ids_in: list[int]) -> str:
    """Execute transfers. IRREVERSIBLE. Requires Session ID."""
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID."
    
    try:
        gw = await client.get_current_gameweek()
        my_team = await client.get_my_team(client.team_id)
        current_map = {p['element']: p['selling_price'] for p in my_team['picks']}
        
        all_players = await client.get_players()
        cost_map = {p.id: p.now_cost for p in all_players}
        
        transfers = []
        for i in range(len(ids_out)):
            if ids_out[i] not in current_map: return f"Error: You do not own player {ids_out[i]}"
            transfers.append({
                "element_out": ids_out[i],
                "element_in": ids_in[i],
                "selling_price": current_map[ids_out[i]],
                "purchase_price": cost_map[ids_in[i]]
            })
            
        payload = TransferPayload(entry=client.team_id, event=gw, transfers=transfers)
        res = await client.execute_transfers(payload)
        return f"Success: {res}"
    except Exception as e:
        return f"Transfer failed: {str(e)}"

@mcp.tool()
async def get_current_gameweek(session_id: str) -> str:
    """
    Get the current or upcoming gameweek information.
    Returns the gameweek that is currently active (before deadline) or the next gameweek (after deadline).
    Use this to determine which gameweek to plan transfers for.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.bootstrap_data or not store.bootstrap_data.events:
        return "Error: Gameweek data not available."
    
    try:
        now = datetime.utcnow()
        
        # First check for is_current flag
        for event in store.bootstrap_data.events:
            if event.is_current:
                deadline = datetime.fromisoformat(event.deadline_time.replace('Z', '+00:00'))
                if now < deadline:
                    # Current gameweek, deadline hasn't passed
                    return (
                        f"**Current Gameweek: {event.name} (ID: {event.id})**\n"
                        f"Deadline: {event.deadline_time}\n"
                        f"Status: Active - deadline not yet passed\n"
                        f"Finished: {event.finished}\n"
                        f"Average Score: {event.average_entry_score or 'N/A'}\n"
                        f"Highest Score: {event.highest_score or 'N/A'}"
                    )
                else:
                    # Deadline passed, look for next gameweek
                    break
        
        # Look for is_next flag (deadline has passed for current)
        for event in store.bootstrap_data.events:
            if event.is_next:
                return (
                    f"**Upcoming Gameweek: {event.name} (ID: {event.id})**\n"
                    f"Deadline: {event.deadline_time}\n"
                    f"Status: Next gameweek (current deadline has passed)\n"
                    f"Released: {event.released}\n"
                    f"Can Enter: {event.can_enter}"
                )
        
        # Fallback: find first unfinished gameweek
        for event in store.bootstrap_data.events:
            if not event.finished:
                return (
                    f"**Upcoming Gameweek: {event.name} (ID: {event.id})**\n"
                    f"Deadline: {event.deadline_time}\n"
                    f"Status: Upcoming\n"
                    f"Released: {event.released}"
                )
        
        return "Error: No active or upcoming gameweek found."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_gameweek_info(session_id: str, gameweek_id: int) -> str:
    """
    Get detailed information about a specific gameweek.
    Includes deadline, scores, top players, and statistics.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.bootstrap_data or not store.bootstrap_data.events:
        return "Error: Gameweek data not available."
    
    try:
        event = next((e for e in store.bootstrap_data.events if e.id == gameweek_id), None)
        if not event:
            return f"Error: Gameweek {gameweek_id} not found."
        
        output = [
            f"**{event.name} (ID: {event.id})**",
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
                f"Highest Scoring Entry: {event.highest_scoring_entry}",
                ""
            ])
            
            if event.top_element_info:
                output.extend([
                    "**Top Performer:**",
                    f"Player ID: {event.top_element_info.id}",
                    f"Points: {event.top_element_info.points}",
                    ""
                ])
        
        if event.most_captained:
            output.extend([
                "**Popular Choices:**",
                f"Most Captained: Player ID {event.most_captained}",
                f"Most Vice-Captained: Player ID {event.most_vice_captained}",
                f"Most Selected: Player ID {event.most_selected}",
                f"Most Transferred In: Player ID {event.most_transferred_in}",
            ])
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_team_info(session_id: str, team_id: int) -> str:
    """
    Get detailed information about a specific Premier League team.
    Includes strength ratings for home/away attack/defence.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    team = store.get_team_by_id(team_id)
    if not team:
        return f"Error: Team with ID {team_id} not found."
    
    output = [
        f"**{team['name']} ({team['short_name']})**",
        f"Team ID: {team['id']}",
        ""
    ]
    
    if team.get('strength'):
        output.append(f"Overall Strength: {team['strength']}")
    
    if team.get('strength_overall_home') or team.get('strength_overall_away'):
        output.extend([
            "",
            "**Overall Strength:**",
            f"Home: {team.get('strength_overall_home', 'N/A')}",
            f"Away: {team.get('strength_overall_away', 'N/A')}",
        ])
    
    if team.get('strength_attack_home') or team.get('strength_attack_away'):
        output.extend([
            "",
            "**Attack Strength:**",
            f"Home: {team.get('strength_attack_home', 'N/A')}",
            f"Away: {team.get('strength_attack_away', 'N/A')}",
        ])
    
    if team.get('strength_defence_home') or team.get('strength_defence_away'):
        output.extend([
            "",
            "**Defence Strength:**",
            f"Home: {team.get('strength_defence_home', 'N/A')}",
            f"Away: {team.get('strength_defence_away', 'N/A')}",
        ])
    
    return "\n".join(output)

@mcp.tool()
async def list_all_teams(session_id: str) -> str:
    """
    List all Premier League teams with their basic information.
    Useful for finding team IDs or comparing team strengths.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    teams = store.get_all_teams()
    if not teams:
        return "Error: Team data not available."
    
    output = ["**Premier League Teams:**\n"]
    
    # Sort by name for easier reading
    teams_sorted = sorted(teams, key=lambda t: t['name'])
    
    for team in teams_sorted:
        strength_info = ""
        if team.get('strength_overall_home') and team.get('strength_overall_away'):
            avg_strength = (team['strength_overall_home'] + team['strength_overall_away']) / 2
            strength_info = f" | Strength: {avg_strength:.0f}"
        
        output.append(
            f"ID {team['id']:2d}: {team['name']:20s} ({team['short_name']}){strength_info}"
        )
    
    return "\n".join(output)

@mcp.tool()
async def search_players_by_team(session_id: str, team_name: str) -> str:
    """
    Search for all players from a specific team.
    Returns player names, positions, prices, and form.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.bootstrap_data:
        return "Error: Player data not available."
    
    try:
        # Find matching teams
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
        
        # Get all players from this team
        players = [
            p for p in store.bootstrap_data.elements
            if p.team == team.id
        ]
        
        if not players:
            return f"No players found for {team.name}"
        
        # Sort by position then by price
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
                f"├─ ID {p.id:3d}: {p.web_name:20s} | £{price:4.1f}m | "
                f"Form: {p.form:4s} | PPG: {p.points_per_game:4s}{status_indicator}{news_indicator}"
            )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_injury_and_lineup_predictions(session_id: str) -> str:
    """
    Get predicted lineups and injury status for upcoming Premier League matches from RotoWire.
    This is crucial for understanding which players are likely to play and who to avoid.
    Shows OUT, DOUBTFUL, and EXPECTED players with confidence ratings.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        scraper = RotoWireLineupScraper()
        lineup_statuses = await scraper.scrape_premier_league_lineups()
        
        if not lineup_statuses:
            return "No lineup predictions available at this time. RotoWire may not have published lineups yet."
        
        # Group by status
        out_players = [s for s in lineup_statuses if s.status == 'OUT']
        doubtful_players = [s for s in lineup_statuses if s.status == 'DOUBTFUL']
        expected_players = [s for s in lineup_statuses if s.status == 'EXPECTED']
        
        output = ["**Premier League Lineup Predictions & Injury Status**\n"]
        
        # OUT players (highest priority)
        if out_players:
            output.append(f"**🚫 OUT ({len(out_players)} players):**")
            for player in sorted(out_players, key=lambda x: x.team):
                output.append(
                    f"├─ {player.player_name} ({player.team}) - {player.reason} "
                    f"[Confidence: {player.confidence:.0%}]"
                )
            output.append("")
        
        # DOUBTFUL players
        if doubtful_players:
            output.append(f"**⚠️ DOUBTFUL ({len(doubtful_players)} players):**")
            for player in sorted(doubtful_players, key=lambda x: x.team):
                output.append(
                    f"├─ {player.player_name} ({player.team}) - {player.reason} "
                    f"[Confidence: {player.confidence:.0%}]"
                )
            output.append("")
        
        # EXPECTED players (only show if there are any)
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
async def get_players_to_avoid(session_id: str) -> str:
    """
    Get a list of players to avoid for transfers based on injury status and lineup predictions.
    Returns players who are OUT or DOUBTFUL with risk levels.
    Use this before making transfers to avoid bringing in injured players.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        scraper = RotoWireLineupScraper()
        lineup_statuses = await scraper.scrape_premier_league_lineups()
        
        if not lineup_statuses:
            return "No lineup data available at this time."
        
        # Convert to AI format
        ai_format = scraper.convert_to_ai_format(lineup_statuses)
        players_to_avoid = ai_format['players_to_avoid']
        
        if not players_to_avoid:
            return "✅ No players currently flagged to avoid based on injury/lineup status."
        
        output = [
            f"**⚠️ Players to Avoid ({len(players_to_avoid)} players)**\n",
            "These players are OUT or DOUBTFUL and should be avoided for transfers:\n"
        ]
        
        # Group by risk level
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
async def check_player_availability(session_id: str, player_name: str) -> str:
    """
    Check if a specific player is available to play based on RotoWire lineup predictions.
    Useful before making a transfer to verify the player is not injured or suspended.
    Requires Session ID and player name (can be partial match).
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        scraper = RotoWireLineupScraper()
        lineup_statuses = await scraper.scrape_premier_league_lineups()
        
        if not lineup_statuses:
            return f"No lineup data available to check {player_name}'s status."
        
        # Find matching players (case-insensitive partial match)
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
        
        # Single match
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
async def list_all_gameweeks(session_id: str) -> str:
    """
    List all gameweeks with their status (finished, current, upcoming).
    Useful for getting an overview of the season.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
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
async def find_player(session_id: str, player_name: str) -> str:
    """
    Find a player by name with intelligent fuzzy matching.
    Handles variations in spelling, partial names, and common nicknames.
    If multiple players match, returns disambiguation options.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.bootstrap_data:
        return "Error: Player data not available."
    
    try:
        matches = store.find_players_by_name(player_name, fuzzy=True)
        
        if not matches:
            return f"No players found matching '{player_name}'. Try a different spelling or use the player's surname."
        
        # If single high-confidence match, return detailed info
        if len(matches) == 1 or (matches[0][1] >= 0.95 and matches[0][1] - matches[1][1] > 0.2):
            player = matches[0][0]
            return _format_player_details(player)
        
        # Multiple matches - need disambiguation
        output = [f"Found {len(matches)} players matching '{player_name}':\n"]
        
        for player, score in matches[:10]:  # Limit to top 10
            price = player.now_cost / 10
            news_indicator = " ⚠️" if player.news else ""
            status_indicator = "" if player.status == 'a' else f" [{player.status}]"
            
            output.append(
                f"├─ ID {player.id}: {player.first_name} {player.second_name} ({player.web_name}) - "
                f"{player.team_name} {player.position} | £{price:.1f}m | "
                f"Form: {player.form} | PPG: {player.points_per_game}{status_indicator}{news_indicator}"
            )
        
        output.append("\nPlease specify the full name or use the player ID for more details.")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_player_details(session_id: str, player_id: int) -> str:
    """
    Get detailed information about a specific player by their ID.
    Includes price, form, team, position, and current status.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    player = store.get_player_by_id(player_id)
    if not player:
        return f"Error: Player with ID {player_id} not found."
    
    return _format_player_details(player)

@mcp.tool()
async def compare_players(session_id: str, player_names: list[str]) -> str:
    """
    Compare multiple players side-by-side.
    Provide a list of 2-5 player names to compare their stats, prices, and form.
    Useful for transfer decisions.
    Requires Session ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.bootstrap_data:
        return "Error: Player data not available."
    
    if len(player_names) < 2:
        return "Error: Please provide at least 2 player names to compare."
    
    if len(player_names) > 5:
        return "Error: Maximum 5 players can be compared at once."
    
    try:
        players_to_compare = []
        ambiguous = []
        
        # Find each player
        for name in player_names:
            matches = store.find_players_by_name(name, fuzzy=True)
            
            if not matches:
                return f"Error: No player found matching '{name}'"
            
            # Check if we have a clear match
            if len(matches) == 1 or (matches[0][1] >= 0.95 and len(matches) > 1 and matches[0][1] - matches[1][1] > 0.2):
                players_to_compare.append(matches[0][0])
            else:
                # Ambiguous - need clarification
                ambiguous.append((name, matches[:3]))
        
        # If any ambiguous matches, ask for clarification
        if ambiguous:
            output = ["Cannot compare - ambiguous player names:\n"]
            for name, matches in ambiguous:
                output.append(f"\n'{name}' could be:")
                for player, score in matches:
                    output.append(f"  - {player.first_name} {player.second_name} ({player.team_name})")
            output.append("\nPlease use more specific names or full names.")
            return "\n".join(output)
        
        # Format comparison
        output = [f"**Player Comparison ({len(players_to_compare)} players)**\n"]
        
        # Header
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
            
            # Additional stats if available
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
        f"ID: {player.id}",
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
    
    # Additional stats
    if hasattr(player, 'selected_by_percent'):
        output.extend([
            "",
            "**Popularity:**",
            f"├─ Selected by: {getattr(player, 'selected_by_percent', 'N/A')}%",
            f"├─ Transfers in (GW): {getattr(player, 'transfers_in_event', 'N/A')}",
            f"├─ Transfers out (GW): {getattr(player, 'transfers_out_event', 'N/A')}",
        ])
    
    # Scoring stats for attackers
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
async def get_player_summary(session_id: str, player_id: int) -> str:
    """
    Get comprehensive player summary including upcoming fixtures, gameweek history, and past season performance.
    This provides detailed stats for a specific FPL player (actual football player, not manager).
    Useful for analyzing player form, fixture difficulty, and historical performance.
    Requires Session ID and player ID.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        # Get player basic info first
        player = store.get_player_by_id(player_id)
        if not player:
            return f"Error: Player with ID {player_id} not found."
        
        # Fetch detailed summary from API
        summary_data = await client.get_element_summary(player_id)
        
        output = [
            f"**{player.web_name}** ({player.first_name} {player.second_name})",
            f"Team: {player.team_name} | Position: {player.position} | Price: £{player.now_cost/10:.1f}m",
            "",
        ]
        
        # Upcoming Fixtures
        fixtures = summary_data.get('fixtures', [])
        if fixtures:
            output.append(f"**Upcoming Fixtures ({len(fixtures)}):**")
            for fixture in fixtures[:5]:  # Show next 5 fixtures
                opponent_id = fixture['team_h'] if not fixture['is_home'] else fixture['team_a']
                opponent = store.get_team_by_id(opponent_id)
                opponent_name = opponent['short_name'] if opponent else f"Team {opponent_id}"
                home_away = "H" if fixture['is_home'] else "A"
                difficulty = "●" * fixture['difficulty']
                
                output.append(
                    f"├─ GW{fixture['event']}: vs {opponent_name} ({home_away}) | "
                    f"Difficulty: {difficulty} ({fixture['difficulty']}/5)"
                )
            output.append("")
        
        # Recent Gameweek History
        history = summary_data.get('history', [])
        if history:
            recent_history = history[-5:]  # Last 5 gameweeks
            output.append(f"**Recent Performance (Last {len(recent_history)} GWs):**")
            
            for gw in recent_history:
                opponent = store.get_team_by_id(gw['opponent_team'])
                opponent_name = opponent['short_name'] if opponent else f"Team {gw['opponent_team']}"
                home_away = "H" if gw['was_home'] else "A"
                
                output.append(
                    f"├─ GW{gw['round']}: {gw['total_points']}pts vs {opponent_name} ({home_away}) | "
                    f"{gw['minutes']}min | G:{gw['goals_scored']} A:{gw['assists']} "
                    f"CS:{gw['clean_sheets']} | Bonus: {gw['bonus']}"
                )
            
            # Calculate averages
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
            for season in history_past[-3:]:  # Last 3 seasons
                output.append(
                    f"├─ {season['season_name']}: {season['total_points']}pts | "
                    f"{season['minutes']}min | G:{season['goals_scored']} A:{season['assists']} | "
                    f"£{season['start_cost']/10:.1f}m → £{season['end_cost']/10:.1f}m"
                )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching player summary: {str(e)}"

@mcp.tool()
async def get_my_fpl_performance(session_id: str, manager_team_id: int) -> str:
    """
    Get FPL manager performance including overall rank, gameweek rank, points, and league standings.
    Use this to check how you or another manager is doing in FPL.
    Requires Session ID and the manager's team ID (entry ID).
    
    Example: If your team ID is 2123402, use that to see your performance.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        # Fetch manager entry data from API
        entry_data = await client.get_manager_entry(manager_team_id)
        
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
        
        # League Information
        leagues = entry_data.get('leagues', {})
        classic_leagues = leagues.get('classic', [])
        
        if classic_leagues:
            output.append(f"**Leagues ({len(classic_leagues)}):**")
            
            # Show Overall league first
            overall_league = next((l for l in classic_leagues if l['name'] == 'Overall'), None)
            if overall_league:
                output.extend([
                    f"\n**Overall League:**",
                    f"├─ Rank: {overall_league['entry_rank']:,} / {overall_league['rank_count']:,}",
                    f"├─ Percentile: Top {overall_league['entry_percentile_rank']}%",
                ])
            
            # Show other leagues (limit to top 5 by rank)
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
        
        # Cup Status
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
        return f"Error fetching manager performance: {str(e)}"

@mcp.tool()
async def get_league_standings(
    session_id: str,
    league_id: int,
    page: int = 1
) -> str:
    """
    Get standings for a specific FPL league.
    Shows manager rankings, points, and team names within the league.
    Use this to see how managers are performing in a private or public league.
    Requires Session ID and league ID (can be found in manager's leagues list).
    
    Example: League ID 899193 from your leagues.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        # Fetch league standings from API
        standings_data = await client.get_league_standings(
            league_id=league_id,
            page_standings=page
        )
        
        league_info = standings_data.get('league', {})
        standings = standings_data.get('standings', {})
        results = standings.get('results', [])
        
        if not results:
            return f"No standings found for league {league_id}"
        
        output = [
            f"**{league_info.get('name', 'League')}**",
            f"League ID: {league_id}",
            f"Total Entries: {standings.get('has_next', False) and 'Many' or len(results)}",
            f"Page: {page}",
            "",
            "**Standings:**",
            ""
        ]
        
        # Format standings table
        for entry in results:
            rank_change = entry['rank'] - entry['last_rank']
            rank_indicator = "↑" if rank_change < 0 else "↓" if rank_change > 0 else "="
            
            output.append(
                f"{entry['rank']:3d}. {rank_indicator} {entry['entry_name']:30s} | "
                f"{entry['player_name']:20s} | "
                f"GW: {entry['event_total']:3d} | Total: {entry['total']:4d} | "
                f"Entry ID: {entry['entry']}"
            )
        
        if standings.get('has_next'):
            output.append(f"\n📄 More entries available. Use page={page + 1} to see next page.")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching league standings: {str(e)}"

@mcp.tool()
async def get_manager_gameweek_team(
    session_id: str,
    manager_team_id: int,
    gameweek: int
) -> str:
    """
    Get a manager's team selection for a specific gameweek.
    Shows the 15 players picked, captain/vice-captain, formation, and points scored.
    Use this to analyze what players a manager selected and how they performed.
    Requires Session ID, manager's team ID (entry ID), and gameweek number.
    
    Example: Team ID 1734732, Gameweek 13
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    try:
        # Fetch gameweek picks from API
        picks_data = await client.get_manager_gameweek_picks(manager_team_id, gameweek)
        
        picks = picks_data.get('picks', [])
        entry_history = picks_data.get('entry_history', {})
        auto_subs = picks_data.get('automatic_subs', [])
        
        if not picks:
            return f"No team data found for manager {manager_team_id} in gameweek {gameweek}"
        
        # Rehydrate player names
        element_ids = [pick['element'] for pick in picks]
        players_info = store.rehydrate_player_names(element_ids)
        
        output = [
            f"**Gameweek {gameweek} Team - Entry ID: {manager_team_id}**",
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
        
        # Separate starting XI and bench
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
        
        # Show automatic substitutions if any
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
async def compare_managers(
    session_id: str,
    manager_team_ids: list[int],
    gameweek: int
) -> str:
    """
    Compare multiple managers' teams for a specific gameweek side-by-side.
    Shows differences in player selection, captaincy choices, and points scored.
    Useful for understanding why one manager outperformed another.
    Requires Session ID, list of 2-4 manager team IDs, and gameweek number.
    
    Example: Compare teams [2123402, 1734732] for gameweek 13
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if len(manager_team_ids) < 2:
        return "Error: Please provide at least 2 manager team IDs to compare."
    
    if len(manager_team_ids) > 4:
        return "Error: Maximum 4 managers can be compared at once."
    
    try:
        # Fetch all teams
        teams_data = []
        for team_id in manager_team_ids:
            picks_data = await client.get_manager_gameweek_picks(team_id, gameweek)
            teams_data.append((team_id, picks_data))
        
        output = [f"**Manager Comparison - Gameweek {gameweek}**\n"]
        
        # Summary comparison
        output.append("**Performance Summary:**")
        for team_id, data in teams_data:
            entry_history = data.get('entry_history', {})
            output.append(
                f"├─ Team {team_id}: {entry_history.get('points', 0)}pts | "
                f"Rank: {entry_history.get('overall_rank', 'N/A'):,} | "
                f"Transfers: {entry_history.get('event_transfers', 0)} "
                f"(-{entry_history.get('event_transfers_cost', 0)}pts)"
            )
        
        output.append("\n**Captain Choices:**")
        for team_id, data in teams_data:
            picks = data.get('picks', [])
            captain_pick = next((p for p in picks if p['is_captain']), None)
            if captain_pick:
                captain_name = store.get_player_name(captain_pick['element'])
                multiplier = captain_pick.get('multiplier', 2)
                output.append(f"├─ Team {team_id}: {captain_name} (x{multiplier})")
        
        # Find common and unique players
        all_players = {}
        for team_id, data in teams_data:
            picks = data.get('picks', [])
            starting_xi = [p['element'] for p in picks if p['position'] <= 11]
            all_players[team_id] = set(starting_xi)
        
        # Common players (in all teams)
        common_players = set.intersection(*all_players.values()) if len(all_players) > 1 else set()
        
        if common_players:
            output.append(f"\n**Common Players ({len(common_players)}):**")
            for element_id in list(common_players)[:10]:  # Limit to 10
                player_name = store.get_player_name(element_id)
                output.append(f"├─ {player_name}")
        
        # Unique players per team
        output.append("\n**Unique Selections:**")
        for team_id in manager_team_ids:
            other_teams = [t for t in manager_team_ids if t != team_id]
            other_players = set()
            for other_id in other_teams:
                other_players.update(all_players.get(other_id, set()))
            
            unique = all_players[team_id] - other_players
            if unique:
                output.append(f"\nTeam {team_id} only:")
                for element_id in list(unique)[:5]:  # Limit to 5
                    player_name = store.get_player_name(element_id)
                    output.append(f"├─ {player_name}")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error comparing managers: {str(e)}"

@mcp.tool()
async def get_fixtures_for_gameweek(session_id: str, gameweek: int) -> str:
    """
    Get all fixtures for a specific gameweek with team names and kickoff times.
    Useful for planning transfers and understanding fixture difficulty.
    Requires Session ID and gameweek number.
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.fixtures_data:
        return "Error: Fixtures data not available."
    
    try:
        # Filter fixtures for the specified gameweek
        gw_fixtures = [f for f in store.fixtures_data if f.event == gameweek]
        
        if not gw_fixtures:
            return f"No fixtures found for gameweek {gameweek}"
        
        output = [
            f"**Gameweek {gameweek} Fixtures ({len(gw_fixtures)} matches)**\n"
        ]
        
        # Sort by kickoff time
        gw_fixtures_sorted = sorted(gw_fixtures, key=lambda x: x.kickoff_time or "")
        
        for fixture in gw_fixtures_sorted:
            team_h = store.get_team_by_id(fixture.team_h)
            team_a = store.get_team_by_id(fixture.team_a)
            
            home_name = team_h['short_name'] if team_h else f"Team {fixture.team_h}"
            away_name = team_a['short_name'] if team_a else f"Team {fixture.team_a}"
            
            status = "✓" if fixture.finished else "○"
            score = f"{fixture.team_h_score}-{fixture.team_a_score}" if fixture.finished else "vs"
            kickoff = fixture.kickoff_time[:16] if fixture.kickoff_time else "TBD"
            
            output.append(
                f"{status} {home_name} {score} {away_name} | "
                f"Kickoff: {kickoff} | "
                f"Difficulty: H:{fixture.team_h_difficulty} A:{fixture.team_a_difficulty}"
            )
        
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching fixtures: {str(e)}"

@mcp.tool()
async def analyze_team_fixtures(session_id: str, team_name: str, num_gameweeks: int = 5) -> str:
    """
    Analyze upcoming fixtures for a specific team to assess difficulty.
    Shows next N gameweeks with opponent strength and home/away status.
    Useful for identifying good times to bring in or sell team assets.
    Requires Session ID, team name, and number of gameweeks to analyze (default: 5).
    """
    client = store.get_client(session_id)
    if not client: return "Error: Invalid/Expired Session ID. Please login_to_fpl."
    
    if not store.bootstrap_data or not store.fixtures_data:
        return "Error: Team or fixtures data not available."
    
    try:
        # Find the team
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
        
        # Get current gameweek
        current_gw = store.get_current_gameweek()
        if not current_gw:
            return "Error: Could not determine current gameweek"
        
        start_gw = current_gw.id
        end_gw = start_gw + num_gameweeks
        
        # Find team's fixtures
        team_fixtures = [
            f for f in store.fixtures_data
            if (f.team_h == team.id or f.team_a == team.id)
            and f.event and start_gw <= f.event < end_gw
            and not f.finished
        ]
        
        if not team_fixtures:
            return f"No upcoming fixtures found for {team.name}"
        
        # Sort by gameweek
        team_fixtures_sorted = sorted(team_fixtures, key=lambda x: x.event or 999)
        
        output = [
            f"**{team.name} ({team.short_name}) - Next {len(team_fixtures_sorted)} Fixtures**\n"
        ]
        
        total_difficulty = 0
        for fixture in team_fixtures_sorted:
            is_home = fixture.team_h == team.id
            opponent_id = fixture.team_a if is_home else fixture.team_h
            opponent = store.get_team_by_id(opponent_id)
            opponent_name = opponent['name'] if opponent else f"Team {opponent_id}"
            
            difficulty = fixture.team_h_difficulty if is_home else fixture.team_a_difficulty
            total_difficulty += difficulty
            
            difficulty_str = "●" * difficulty + "○" * (5 - difficulty)
            home_away = "H" if is_home else "A"
            kickoff = fixture.kickoff_time[:10] if fixture.kickoff_time else "TBD"
            
            output.append(
                f"GW{fixture.event}: vs {opponent_name:20s} ({home_away}) | "
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