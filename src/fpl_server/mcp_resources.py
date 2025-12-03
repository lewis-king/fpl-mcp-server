"""
FPL MCP Resources - Read-only data access via URI templates.

Resources expose FPL data that can be accessed multiple times efficiently.
They represent GET-like operations without side effects.
"""

from datetime import datetime
from .state import store
from .mcp_tools import mcp, _get_client
from .rotowire_scraper import RotoWireLineupScraper


# ============================================================================
# BOOTSTRAP DATA RESOURCES (Static)
# ============================================================================

@mcp.resource("fpl://bootstrap/players")
async def get_all_players_resource() -> str:
    """Get all FPL players with basic stats and prices."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
    if not store.bootstrap_data or not store.bootstrap_data.elements:
        return "Error: Player data not available."
    
    try:
        players = store.bootstrap_data.elements
        
        output = [f"**All FPL Players ({len(players)} total)**\n"]
        
        # Group by position
        positions = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
        for p in players:
            if p.position in positions:
                positions[p.position].append(p)
        
        for pos, players_list in positions.items():
            output.append(f"\n**{pos} ({len(players_list)} players):**")
            # Sort by price descending, show top 10
            sorted_players = sorted(players_list, key=lambda x: x.now_cost, reverse=True)[:10]
            for p in sorted_players:
                price = p.now_cost / 10
                news_indicator = " ⚠️" if p.news else ""
                output.append(
                    f"├─ {p.web_name:15s} ({p.team_name:15s}) | £{price:4.1f}m | "
                    f"Form: {p.form:4s} | PPG: {p.points_per_game:4s}{news_indicator}"
                )
            if len(players_list) > 10:
                output.append(f"└─ ... and {len(players_list) - 10} more")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.resource("fpl://bootstrap/teams")
async def get_all_teams_resource() -> str:
    """Get all Premier League teams with strength ratings."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
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


@mcp.resource("fpl://bootstrap/gameweeks")
async def get_all_gameweeks_resource() -> str:
    """Get all gameweeks with their status for the season."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
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


@mcp.resource("fpl://current-gameweek")
async def get_current_gameweek_resource() -> str:
    """Get the current or upcoming gameweek information."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
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


# ============================================================================
# PLAYER RESOURCES (Dynamic)
# ============================================================================

@mcp.resource("fpl://player/{player_name}")
async def get_player_resource(player_name: str) -> str:
    """Get detailed information about a specific player by name."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
    matches = store.find_players_by_name(player_name, fuzzy=True)
    
    if not matches:
        return f"No player found matching '{player_name}'"
    
    if len(matches) > 1 and matches[0][1] < 0.95:
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
    
    player = matches[0][0]
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


@mcp.resource("fpl://player/{player_name}/summary")
async def get_player_summary_resource(player_name: str) -> str:
    """Get comprehensive player summary including fixtures, history, and past seasons."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    try:
        await store.ensure_bootstrap_data(client)
        
        # Find player by name
        matches = store.find_players_by_name(player_name, fuzzy=True)
        if not matches:
            return f"No player found matching '{player_name}'"
        
        if len(matches) > 1 and matches[0][1] < 0.95:
            return f"Ambiguous player name. Use fpl://player/{player_name} to see all matches"
        
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


# ============================================================================
# TEAM RESOURCES (Dynamic)
# ============================================================================

@mcp.resource("fpl://team/{team_name}")
async def get_team_resource(team_name: str) -> str:
    """Get detailed information about a Premier League team including strength ratings."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
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


@mcp.resource("fpl://team/{team_name}/squad")
async def get_team_squad_resource(team_name: str) -> str:
    """Get all players from a specific team organized by position."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
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


@mcp.resource("fpl://team/{team_name}/fixtures/{num_gameweeks}")
async def get_team_fixtures_resource(team_name: str, num_gameweeks: int = 5) -> str:
    """Get upcoming fixtures for a team with difficulty ratings. Default num_gameweeks is 5."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    await store.ensure_fixtures_data(client)
    
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


# ============================================================================
# GAMEWEEK RESOURCES (Dynamic)
# ============================================================================

@mcp.resource("fpl://gameweek/{gameweek_number}")
async def get_gameweek_resource(gameweek_number: int) -> str:
    """Get detailed information about a specific gameweek."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_bootstrap_data(client)
    
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


@mcp.resource("fpl://gameweek/{gameweek_number}/fixtures")
async def get_gameweek_fixtures_resource(gameweek_number: int) -> str:
    """Get all fixtures for a specific gameweek."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    await store.ensure_fixtures_data(client)
    
    if not store.fixtures_data:
        return "Error: Fixtures data not available."
    
    try:
        gw_fixtures = [f for f in store.fixtures_data if f.event == gameweek_number]
        
        if not gw_fixtures:
            return f"No fixtures found for gameweek {gameweek_number}"
        
        # Enrich fixtures with team names
        gw_fixtures_enriched = store.enrich_fixtures(gw_fixtures)
        
        output = [
            f"**Gameweek {gameweek_number} Fixtures ({len(gw_fixtures_enriched)} matches)**\n"
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


# ============================================================================
# MY ACCOUNT RESOURCES
# ============================================================================

@mcp.resource("fpl://my/info")
async def get_my_info_resource() -> str:
    """Get your FPL account information including leagues."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
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


@mcp.resource("fpl://my/squad")
async def get_my_squad_resource() -> str:
    """Get your current team squad with chips and transfer information."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    try:
        entry_id = store.get_user_entry_id(client)
        if not entry_id:
            return "Error: Could not determine your entry ID. Please try logging in again."
        
        my_team = await client.get_my_team(entry_id)
        all_players = await client.get_players()
        p_map = {p.id: p for p in all_players}
        
        # Transfer info
        transfers = my_team['transfers']
        bank = transfers['bank'] / 10
        free_transfers = transfers['limit'] - transfers['made']
        transfer_cost = transfers['cost']
        squad_value = transfers['value'] / 10
        
        output = [
            f"**My Team**",
            f"Squad Value: £{squad_value:.1f}m | Bank: £{bank:.1f}m",
            f"Free Transfers: {free_transfers} | Transfer Cost: {transfer_cost} pts",
            ""
        ]
        
        # Chips info
        chips = my_team.get('chips', [])
        if chips:
            available_chips = [c for c in chips if c['status_for_entry'] == 'available']
            played_chips = [c for c in chips if c['status_for_entry'] == 'played']
            
            if available_chips:
                chip_icons = {
                    'bboost': '📊',
                    'freehit': '🎯',
                    '3xc': '⭐',
                    'wildcard': '🃏'
                }
                chips_str = ', '.join([f"{chip_icons.get(c['name'], '🎴')} {c['name'].upper()}" for c in available_chips])
                output.append(f"**Available Chips:** {chips_str}")
            
            if played_chips:
                output.append(f"**Played Chips:** {', '.join([c['name'].upper() for c in played_chips])}")
            
            output.append("")
        
        # Squad
        output.append("**Starting XI:**")
        starting = [p for p in my_team['picks'] if p['position'] <= 11]
        for pick in starting:
            p = p_map.get(pick['element'])
            role = " (C)" if pick['is_captain'] else " (VC)" if pick['is_vice_captain'] else ""
            output.append(f"{pick['position']:2d}. {p.web_name} ({p.team_name}): £{pick['selling_price']/10:.1f}m{role}")
        
        output.append("\n**Bench:**")
        bench = [p for p in my_team['picks'] if p['position'] > 11]
        for pick in bench:
            p = p_map.get(pick['element'])
            output.append(f"{pick['position']:2d}. {p.web_name} ({p.team_name}): £{pick['selling_price']/10:.1f}m")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.resource("fpl://my/performance")
async def get_my_performance_resource() -> str:
    """Get your FPL performance including ranks and league standings."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
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


# ============================================================================
# LEAGUE RESOURCES (Dynamic)
# ============================================================================

@mcp.resource("fpl://league/{league_name}/standings/{page}")
async def get_league_standings_resource(league_name: str, page: int = 1) -> str:
    """Get standings for a specific league by name. Default page is 1."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    try:
        # Find league by name
        league_info = await store.find_league_by_name(client, league_name)
        if not league_info:
            return f"Could not find a league named '{league_name}' in your leagues. Use fpl://my/info to see your leagues."
        
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


@mcp.resource("fpl://manager/{manager_name}/team/{league_name}/{gameweek}")
async def get_manager_team_resource(manager_name: str, league_name: str, gameweek: int) -> str:
    """Get a manager's team selection for a specific gameweek."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
    try:
        # Find league first
        league_info = await store.find_league_by_name(client, league_name)
        if not league_info:
            return f"Could not find league '{league_name}'. Use fpl://my/info to see your leagues."
        
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


# ============================================================================
# INJURY & LINEUP RESOURCES
# ============================================================================

@mcp.resource("fpl://injuries")
async def get_injuries_resource() -> str:
    """Get injury and lineup predictions from RotoWire."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
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


@mcp.resource("fpl://injuries/avoid")
async def get_players_to_avoid_resource() -> str:
    """Get players to avoid based on injury and lineup status."""
    client = _get_client()
    if not client:
        return "Error: Not authenticated. Please use login_to_fpl tool first."
    
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