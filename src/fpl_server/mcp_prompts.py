"""
FPL MCP Prompts - Reusable analysis templates for LLM guidance.

Prompts provide structured templates that guide the LLM in analyzing FPL data
and making strategic recommendations. They define the analysis framework and
expected output format.
"""

from .mcp_tools import mcp


@mcp.prompt()
def analyze_squad_performance(num_gameweeks: int = 5) -> str:
    """
    Generate a prompt for analyzing squad performance over recent gameweeks.
    
    This prompt guides the LLM to perform comprehensive squad analysis including:
    - Points per game averages
    - Minutes played and rotation risk
    - Recent form trends (improving/declining/stable)
    - Did Not Play (DNP) instances
    - Community transfer sentiment
    - Categorization into star/solid/underperformers
    - Specific transfer recommendations
    
    Args:
        num_gameweeks: Number of recent gameweeks to analyze (default: 5)
    """
    return f"""Analyze my FPL squad's performance over the last {num_gameweeks} gameweeks.

**Analysis Framework:**

For each player in my squad, evaluate:

1. **Performance Metrics:**
   - Points per game average over last {num_gameweeks} GWs
   - Total points accumulated
   - Minutes played per game
   - Games where player did not play (DNP)

2. **Form Trend Analysis:**
   - Compare last 3 gameweeks vs previous games
   - Classify as: 📈 Improving, 📉 Declining, or ➡️ Stable
   - Identify any concerning patterns

3. **Community Sentiment:**
   - Net transfer balance (buying vs selling pressure)
   - Recent transfer trends
   - Ownership changes

4. **Player Categorization:**
   - ⭐ **Star Performers**: >5 pts/game - Essential to keep
   - ✅ **Solid Performers**: 2.5-5 pts/game - Reliable options
   - 🚨 **Underperformers**: <2.5 pts/game - Transfer candidates

**For Underperformers, provide:**
- Specific reasons for poor performance
- Injury/rotation status check
- Upcoming fixture difficulty
- Price efficiency analysis
- Community sentiment context
- Clear transfer recommendation with urgency level:
  * 🚨 URGENT: Injured/suspended or DNP last game
  * ⚠️ HIGH: Low minutes or very poor form
  * 🟡 MEDIUM: Tough fixtures or moderate concerns
  * 🟢 LOW: Monitor situation

**Summary Section:**
- Count of players in each category
- Priority transfer target (worst performer)
- Overall squad health assessment
- Free transfers available consideration

**Data Access:**
Use these resources to gather the required data:
- `fpl://my/squad` - Current squad with chips and transfers info
- `fpl://player/{{player_name}}/summary` - Detailed player history for each squad member
- `fpl://injuries` - Check injury status for any concerns

**Output Format:**
Present findings in a clear, actionable format with:
- Visual indicators (emojis) for quick scanning
- Specific player names and statistics
- Prioritized recommendations
- Context for decision-making"""


@mcp.prompt()
def recommend_transfers(free_transfers: int = 1) -> str:
    """
    Generate a prompt for transfer recommendations based on available free transfers.
    
    This prompt guides the LLM to analyze the squad and recommend optimal transfer
    strategy considering:
    - Player availability (injuries, suspensions)
    - Recent performance and form
    - Upcoming fixture difficulty
    - Points hit economics
    - Strategic timing
    
    Args:
        free_transfers: Number of free transfers available (default: 1)
    """
    return f"""Analyze my squad and recommend transfer strategy.

**Current Situation:**
- Free Transfers Available: {free_transfers}
- Transfer Cost: 4 points per additional transfer

**Analysis Framework:**

1. **Player Priority Scoring:**
   For each squad player, calculate priority score based on:
   - **Availability Status** (+100 pts): Injured, suspended, doubtful, unavailable
   - **DNP Last Game** (+50 pts): Did not play in most recent gameweek
   - **Fixture Difficulty** (+15-30 pts): Hard upcoming fixtures (avg 3.5+/5)
   - **Poor Form** (+10-25 pts): Low form score (<3)
   - **Low Minutes** (+20 pts): Less than 200 minutes total

2. **Strategic Advice by Free Transfers:**

   **{free_transfers} Free Transfer(s):**
   {'🔴 **0 Free Transfers** - Only take a hit (-4pts) if:' if free_transfers == 0 else ''}
   {'   • Player is injured/suspended (unavailable)' if free_transfers == 0 else ''}
   {'   • Replacement has a double gameweek' if free_transfers == 0 else ''}
   {'   • Replacement expected to score 6+ more points (to break even)' if free_transfers == 0 else ''}
   {'   • Otherwise, wait for next gameweek to bank a free transfer' if free_transfers == 0 else ''}
   
   {'🟡 **1 Free Transfer** - Consider:' if free_transfers == 1 else ''}
   {'   • Banking if no urgent issues (gives 2 FT next week)' if free_transfers == 1 else ''}
   {'   • Use for injured/suspended players' if free_transfers == 1 else ''}
   {'   • Use for players with very poor fixtures' if free_transfers == 1 else ''}
   {'   • Banking provides more flexibility next week' if free_transfers == 1 else ''}
   
   {'🟢 **2 Free Transfers** - Good flexibility:' if free_transfers >= 2 else ''}
   {'   • Address top 2 priority problems' if free_transfers >= 2 else ''}
   {'   • Don\'t waste transfers - only make valuable moves' if free_transfers >= 2 else ''}
   {'   • Unused transfers don\'t roll over beyond 2' if free_transfers >= 2 else ''}

3. **Transfer Candidates Analysis:**
   Identify top 5 players to consider transferring out:
   - Priority score and specific reasons
   - Next 3 fixtures with difficulty visualization
   - Bench vs starting XI status
   - Urgency level:
     * 🚨 URGENT (100+ pts): Transfer out immediately
     * ⚠️ HIGH (50+ pts): Strong transfer candidate
     * 🟡 MEDIUM (30+ pts): Consider if spare FT
     * 🟢 LOW (<30 pts): Monitor, not urgent

4. **Points Hit Economics:**
   - Each additional transfer costs 4 points
   - Replacement must score 6+ more points to break even:
     * 4 points to recover the hit
     * 2+ points to actually gain value
   - Only justified for injured players or exceptional opportunities

5. **Timing Considerations:**
   - Make transfers early in week to monitor price changes
   - Wait for Friday press conferences for injury news
   - Check lineup predictions before finalizing
   - Consider banking transfers for future flexibility

**Data Access:**
Use these resources:
- `fpl://my/squad` - Current squad with transfer info
- `fpl://injuries` - Injury and lineup predictions
- `fpl://injuries/avoid` - Players to avoid
- `fpl://player/{{player_name}}/summary` - Detailed player analysis
- `fpl://team/{{team_name}}/fixtures` - Fixture difficulty

**Output Format:**
1. Strategic advice summary based on free transfers
2. Top 5 transfer candidates with:
   - Priority score and reasons
   - Fixture difficulty visualization
   - Specific recommendations
3. Points hit economics explanation
4. Timing advice"""


@mcp.prompt()
def recommend_chip_strategy() -> str:
    """
    Generate a prompt for chip strategy recommendations.
    
    This prompt guides the LLM to analyze available chips and recommend optimal
    timing based on:
    - Double gameweeks (DGW) detection
    - Blank gameweeks (BGW) detection
    - Squad composition and quality
    - Fixture difficulty patterns
    - Chip-specific strategies
    """
    return """Analyze available chips and recommend optimal timing strategy.

**Chip Analysis Framework:**

For each available chip, provide strategic recommendations:

1. **🃏 WILDCARD Strategy:**
   - **Optimal Timing**: Use 1 GW before Double Gameweeks (DGW)
   - **Squad Health Check**: Count injured/unavailable players
   - **Trigger Points**:
     * DGW detected within next 5 gameweeks → HIGH priority
     * 3+ players injured/unavailable → HIGH priority
     * Major squad overhaul needed → MEDIUM priority
   - **Pro Tip**: Maximize new players' potential by wildcarding before DGW

2. **🎯 FREE HIT Strategy:**
   - **Optimal Timing**: Save for Blank Gameweeks (BGW)
   - **BGW Detection**: When <60% of teams play (typically <12 teams)
   - **Trigger Points**:
     * BGW within 3 gameweeks → HIGH priority
     * BGW within 8 gameweeks → MEDIUM priority
     * No BGW but DGW available → LOW priority (backup option)
   - **Pro Tip**: Best used when few teams play, allows one-week team transformation

3. **⭐ TRIPLE CAPTAIN Strategy:**
   - **Optimal Timing**: Premium players (£9m+) in DGW
   - **Analysis Required**:
     * Identify premium players in squad
     * Check next 5 fixtures for each premium
     * Score opportunities:
       - DGW (+50 pts)
       - Easy fixtures (+10-50 pts based on difficulty)
       - Home advantage (+5 pts)
       - Current form bonus
   - **Trigger Points**:
     * Premium has DGW → HIGH priority
     * Premium has easy home fixture → MEDIUM priority
     * No premiums in squad → LOW priority
   - **Pro Tip**: Maximum impact on high-scoring players in double gameweeks

4. **📊 BENCH BOOST Strategy:**
   - **Optimal Timing**: When bench players have DGW
   - **Bench Quality Check**:
     * Average minutes played (need 300+ for strong bench)
     * Points per game of bench players
   - **Trigger Points**:
     * 2+ bench players have DGW → HIGH priority
     * Strong bench (avg 300+ mins) + DGW → HIGH priority
     * Weak bench (avg <300 mins) → LOW priority (improve first)
   - **Pro Tip**: Maximize returns when bench players have double gameweeks

**Fixture Analysis (Next 10 Gameweeks):**
Scan for:
- **Double Gameweeks (DGW)**: Teams playing twice in one GW
- **Blank Gameweeks (BGW)**: <60% of teams playing
- Pattern recognition for optimal chip timing

**Priority Ranking:**
Sort recommendations by:
- 🔴 HIGH: Immediate opportunity or urgent need
- 🟡 MEDIUM: Good opportunity within 5 gameweeks
- 🟢 LOW: No immediate opportunity, save for later

**Data Access:**
Use these resources:
- `fpl://my/squad` - Current squad with chips status
- `fpl://current-gameweek` - Current gameweek info
- `fpl://gameweek/{{gw}}/fixtures` - Fixtures for each upcoming GW
- `fpl://player/{{player_name}}/summary` - Premium player analysis

**Output Format:**
1. Available chips list
2. For each chip:
   - Strategic recommendation
   - Specific gameweek suggestion (if applicable)
   - Priority level with reasoning
   - Pro tip
3. Upcoming fixture overview (next 6 GWs)
   - Highlight DGWs and BGWs
   - Team counts per gameweek"""


@mcp.prompt()
def compare_players(*player_names: str) -> str:
    """
    Generate a prompt for comparing multiple players side-by-side.
    
    This prompt guides the LLM to perform comprehensive player comparison
    considering all relevant FPL metrics.
    
    Args:
        *player_names: Variable number of player names to compare (2-5 players)
    """
    players_str = ", ".join(player_names) if player_names else "{{player1}}, {{player2}}, ..."
    num_players = len(player_names) if player_names else "2-5"
    
    return f"""Compare these FPL players side-by-side: {players_str}

**Comparison Framework:**

For each player ({num_players} players), analyze:

1. **Basic Information:**
   - Full name and web name
   - Team and position
   - Current price
   - Ownership percentage

2. **Performance Metrics:**
   - Form (recent performance indicator)
   - Points per game (PPG)
   - Total points this season
   - Minutes played
   - Games played

3. **Availability & Status:**
   - Current status (available/injured/doubtful/suspended)
   - Any injury news or concerns
   - Rotation risk assessment

4. **Goal Contributions:**
   - Goals scored
   - Assists provided
   - Expected goals (xG) if available
   - Expected assists (xA) if available

5. **Defensive Stats** (for defenders/goalkeepers):
   - Clean sheets
   - Goals conceded
   - Bonus points earned

6. **Upcoming Fixtures:**
   - Next 5 fixtures
   - Fixture difficulty rating
   - Home vs away balance
   - Double gameweek opportunities

7. **Value Analysis:**
   - Price per point ratio
   - Recent price changes
   - Transfer trends (in/out)

**Comparison Output:**

Present findings in a structured format:

1. **Quick Summary Table:**
   - Side-by-side key metrics
   - Visual indicators for best in each category

2. **Detailed Analysis:**
   - Best value for money
   - Most in-form player
   - Best fixtures ahead
   - Injury/availability concerns
   - Rotation risk comparison

3. **Recommendation:**
   - Which player to choose and why
   - Specific use cases for each player
   - Transfer priority if considering multiple

**Data Access:**
For each player, use:
- `fpl://player/{{player_name}}` - Basic player info
- `fpl://player/{{player_name}}/summary` - Comprehensive stats with fixtures

**Output Format:**
- Clear visual comparison
- Highlight best performer in each category
- Provide actionable recommendation
- Consider user's specific needs (budget, position, fixtures)"""


@mcp.prompt()
def analyze_team_fixtures(team_name: str, num_gameweeks: int = 5) -> str:
    """
    Generate a prompt for analyzing a team's upcoming fixtures.
    
    This prompt guides the LLM to assess fixture difficulty and identify
    optimal times to invest in or avoid a team's assets.
    
    Args:
        team_name: Name of the team to analyze
        num_gameweeks: Number of gameweeks to analyze (default: 5)
    """
    return f"""Analyze {team_name}'s upcoming fixtures for the next {num_gameweeks} gameweeks.

**Fixture Analysis Framework:**

1. **Fixture Difficulty Assessment:**
   For each upcoming fixture:
   - Opponent strength
   - Home vs Away
   - Difficulty rating (1-5 scale):
     * 1-2: Easy (favorable for attacking returns)
     * 3: Moderate (neutral)
     * 4-5: Hard (difficult for returns)

2. **Pattern Analysis:**
   - Average difficulty rating across all fixtures
   - Home/away balance
   - Consecutive difficult/easy fixtures
   - Any double gameweeks detected

3. **Strategic Insights:**
   
   **For Attacking Assets (Forwards/Midfielders):**
   - Best gameweeks to captain {team_name} players
   - When to bring in {team_name} attackers
   - When to avoid due to tough fixtures
   
   **For Defensive Assets (Defenders/Goalkeeper):**
   - Clean sheet probability by fixture
   - Best gameweeks for defensive returns
   - When to bench {team_name} defenders

4. **Overall Assessment:**
   Classify the fixture run as:
   - **Favorable** (avg difficulty <3.0): Good time to invest
   - **Moderate** (avg difficulty 3.0-3.5): Neutral, case-by-case
   - **Difficult** (avg difficulty >3.5): Consider avoiding

5. **Timing Recommendations:**
   - Specific gameweeks to target for transfers in
   - Gameweeks to avoid {team_name} assets
   - Long-term fixture outlook

**Data Access:**
Use: `fpl://team/{team_name}/fixtures?num_gameweeks={num_gameweeks}`

**Output Format:**
1. Fixture list with difficulty visualization
2. Average difficulty rating
3. Overall assessment (Favorable/Moderate/Difficult)
4. Specific recommendations:
   - When to bring in {team_name} players
   - Which positions to target (attack vs defense)
   - When to avoid or transfer out
5. Best gameweeks for captaincy consideration"""


@mcp.prompt()
def compare_managers(league_name: str, gameweek: int, *manager_names: str) -> str:
    """
    Generate a prompt for comparing managers' teams in a league.
    
    This prompt guides the LLM to analyze differences in team selection,
    strategy, and performance between multiple managers.
    
    Args:
        league_name: Name of the league
        gameweek: Gameweek number to analyze
        *manager_names: Variable number of manager names (2-4 managers)
    """
    managers_str = ", ".join(manager_names) if manager_names else "{{manager1}}, {{manager2}}, ..."
    num_managers = len(manager_names) if manager_names else "2-4"
    
    return f"""Compare these managers' teams in {league_name} for Gameweek {gameweek}: {managers_str}

**Comparison Framework:**

Analyze {num_managers} managers across multiple dimensions:

1. **Performance Summary:**
   For each manager:
   - Gameweek points scored
   - Overall rank
   - Total points for season
   - Transfers made and cost
   - Points left on bench

2. **Team Selection Analysis:**
   
   **Captain Choices:**
   - Who did each manager captain?
   - Captain points scored
   - Was it a differential or template choice?
   
   **Formation & Structure:**
   - Formation used (e.g., 3-4-3, 4-3-3)
   - Premium player allocation
   - Budget distribution

3. **Player Overlap Analysis:**
   
   **Common Players:**
   - Players owned by all managers
   - Template players (high ownership)
   - How many players in common?
   
   **Differential Picks:**
   - Unique players per manager
   - Which differentials performed well?
   - Which differentials flopped?

4. **Strategic Decisions:**
   
   **Chip Usage:**
   - Did anyone use a chip this gameweek?
   - Impact of chip usage on points
   
   **Transfer Strategy:**
   - Number of transfers made
   - Points hit taken (if any)
   - Transfer effectiveness

5. **Performance Drivers:**
   
   **Why did one manager outperform?**
   - Better captain choice?
   - Successful differentials?
   - Avoided blanks?
   - Chip usage?
   
   **Key Differences:**
   - Tactical variations
   - Risk vs safety approach
   - Budget allocation differences

6. **Bench Analysis:**
   - Points left on bench per manager
   - Bench strength comparison
   - Auto-substitutions made

**Data Access:**
For each manager, use:
`fpl://manager/{{manager_name}}/team/{league_name}/{gameweek}`

**Output Format:**
1. Performance summary table
2. Captain choices comparison
3. Common players list
4. Unique selections per manager
5. Key performance drivers analysis
6. Strategic insights:
   - What worked well?
   - What didn't work?
   - Lessons learned
7. Recommendations for catching up (if behind)"""


@mcp.prompt()
def find_league_differentials(league_name: str, max_ownership: float = 30.0) -> str:
    """
    Generate a prompt for finding differential players in a league.
    
    This prompt guides the LLM to identify low-owned players that could
    provide a competitive advantage in a specific league.
    
    Args:
        league_name: Name of the league to analyze
        max_ownership: Maximum ownership % to consider as differential (default: 30%)
    """
    return f"""Find differential players for competitive advantage in {league_name}.

**Differential Analysis Framework:**

1. **Definition:**
   Differentials are players owned by <{max_ownership}% of managers in your league
   who have strong potential for points.

2. **League Context Analysis:**
   - Total managers in league
   - Current league standings
   - Template players (high ownership)
   - Common captain choices

3. **Differential Categories:**
   
   **Premium Differentials (£9m+):**
   - High-priced players with low league ownership
   - Potential for big hauls
   - Higher risk but higher reward
   
   **Mid-Price Differentials (£6-9m):**
   - Value picks with good fixtures
   - Consistent performers
   - Lower risk, steady returns
   
   **Budget Differentials (<£6m):**
   - Enablers with attacking potential
   - Rotation risks but cheap
   - Good for bench options

4. **Evaluation Criteria:**
   For each differential candidate:
   - Current form and points per game
   - Upcoming fixture difficulty
   - Minutes played (rotation risk)
   - Injury status
   - League ownership %
   - Overall ownership %
   - Price and value

5. **Strategic Recommendations:**
   
   **When to use differentials:**
   - Chasing league leaders (need to take risks)
   - Good fixture runs ahead
   - Template players have tough fixtures
   
   **When to avoid differentials:**
   - Leading the league (play it safe)
   - Differential has injury concerns
   - Rotation risk too high

6. **Risk Assessment:**
   - High Risk: Low ownership, rotation risk, tough fixtures
   - Medium Risk: Moderate ownership, some rotation, mixed fixtures
   - Low Risk: Decent ownership, nailed on, good fixtures

**Data Access:**
- `fpl://league/{league_name}/standings` - League ownership patterns
- `fpl://bootstrap/players` - All players with ownership
- `fpl://player/{{player_name}}/summary` - Detailed player analysis
- `fpl://team/{{team_name}}/fixtures` - Fixture difficulty

**Output Format:**
1. League template analysis (most owned players)
2. Differential candidates by price bracket:
   - Premium differentials
   - Mid-price differentials
   - Budget differentials
3. For each differential:
   - League ownership %
   - Overall ownership %
   - Form and fixtures
   - Risk level
   - Recommendation
4. Strategic advice:
   - Best differentials for your situation
   - Timing for bringing them in
   - Risk vs reward assessment"""