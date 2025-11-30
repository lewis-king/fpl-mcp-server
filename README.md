# 🏆 FPL MCP Server - Your AI-Powered Fantasy Premier League Assistant

> Control your Fantasy Premier League team with your favourite LLM to help inform your decisions and gain more contextual insights based for your team


A secure, feature-rich Model Context Protocol (MCP) server that connects your LLM (like Claude) to the Fantasy Premier League API, enabling intelligent team management, competitor analysis, and data-driven decision making.

## 🌟 Why This Tool?

Fantasy Premier League is complex. With 20 teams, 600+ players, injuries, form changes, and fixture difficulty to track, making optimal decisions is challenging. This MCP server gives your AI assistant **complete access** to FPL data, enabling:

- 🔍 **Deep Competitor Analysis** - Spy on league rivals, analyze their teams, and understand why they're winning
- 📊 **Intelligent Player Research** - Get comprehensive stats, fixture analysis, and injury updates
- 🎯 **Strategic Planning** - Analyze fixture difficulty, identify transfer targets, and optimize your squad
- 🏅 **League Intelligence** - Track standings, compare teams, and gain competitive insights
- 🤖 **AI-Powered Decisions** - Let your LLM crunch the numbers and suggest optimal strategies

## ✨ Key Features

### 🔐 Secure Authentication
- **Out-of-Band Login** - Your FPL credentials never touch the LLM
- **Multi-User Support** - Multiple sessions with isolated authentication
- **Session Management** - Secure token-based API access

### 📈 Comprehensive Data Access

#### Your Team Management
- View current squad with prices and roles
- Execute transfers with validation
- Check team value and bank balance
- Track transfer history and costs

#### Player Intelligence
- **Smart Search** - Fuzzy name matching handles typos and variations
- **Detailed Stats** - Form, points per game, total points, ownership
- **Injury Reports** - Real-time lineup predictions from RotoWire
- **Fixture Analysis** - Upcoming opponents with difficulty ratings
- **Historical Performance** - Past gameweek and season statistics
- **Player Comparison** - Side-by-side analysis of multiple players

#### Competitive Analysis
- **League Standings** - View any league with pagination support
- **Manager Performance** - Deep dive into any manager's stats and rankings
- **Team Inspection** - See exactly what players competitors picked each gameweek
- **Head-to-Head Comparison** - Compare multiple managers' teams side-by-side
- **Captain Choices** - Analyze captaincy decisions across your league

#### Strategic Planning
- **Fixture Difficulty** - Analyze team schedules for transfer timing
- **Gameweek Fixtures** - Complete fixture list with kickoff times
- **Top Performers** - Best players by position based on form
- **Team Squads** - Browse all players from specific teams
- **Injury Avoidance** - Identify players to avoid before transfers

### 🚀 Advanced Capabilities

#### Circular Data Flow with Friendly Names
The server enables **natural, circular exploration** of FPL data using friendly names:
```
Your Performance → Your Leagues → League Standings → Competitor Teams → Player Analysis
     ↓                                                      ↓
  Compare Teams ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

Example workflow using **only friendly names**:
1. "How am I doing?" → Automatically uses your entry, shows your leagues
2. "Show Greatest Fantasy Footy standings" → Find top competitors by league name
3. "What team did Jaakko pick in GW13?" → Analyze selections by manager name
4. "Compare my team to Jaakko's" → Understand performance differences
5. "Tell me about Haaland's fixtures" → Research players by name
6. "Compare Salah and Palmer" → Direct player comparison by names

**No IDs needed anywhere!** The system resolves all names internally.

#### Smart Caching
- **4-Hour TTL** - Bootstrap and fixtures data cached locally
- **Automatic Refresh** - Data updates when cache expires
- **Fallback Support** - Uses expired cache if API fails
- **Fast Responses** - Instant access to cached data

#### Player Name Rehydration
- **Automatic Translation** - Element IDs converted to player names
- **Rich Context** - Full player info (team, position, price, form)
- **Seamless Experience** - No manual ID lookups needed

## 📋 Prerequisites

1. **Install `uv`** (An extremely fast Python package manager):
   * **Mac/Linux**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   * **Windows**:
     ```powershell
     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```

## 🚀 Installation & Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd fpl-mcp-server

# Install dependencies
uv sync

# Install Playwright browsers (required for login automation)
uv run playwright install chromium
```

### 2. Verify Installation (Optional)

Test the server locally before connecting to Claude:

```bash
uv run --env PYTHONPATH=src python -m fpl_server.main
```

You should see:
```text
Starting FPL Web Auth on http://localhost:8000
Starting MCP Server (Stdio)...
```

Press `Ctrl+C` to stop.

### 3. Connect to Claude Desktop

#### Get Your Project Path

* **Mac/Linux**: Run `pwd` in the project folder
* **Windows**: Run `cd` in the project folder

Copy the full absolute path.

#### Configure Claude

Open Claude's config file:
* **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the FPL server (replace `/ABSOLUTE/PATH/TO/fpl-mcp-server` with your path):

```json
{
  "mcpServers": {
    "fpl": {
      "command": "uv",
      "args": [
        "run",
        "--env", "PYTHONPATH=src",
        "python",
        "-m",
        "fpl_server.main"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/fpl-mcp-server"
    }
  }
}
```

#### Restart Claude

Quit Claude completely and reopen. An error notification popup will appear if something is wrong with connecting the MCP server. If not error, this is a good sign, but go to settings and check connectors to confirm fpl-mcp-server is listed there.

## 💡 Usage Examples

### 🎯 Natural Conversation Flow

The server uses **friendly names** instead of IDs, enabling natural conversations:

### Getting Started
```
You: "Log me into FPL"
Claude: [Provides secure login link]
You: [Click link, enter credentials, confirm]
You: "I'm done"
Claude: "✅ Authentication successful! Your session is now active."
```

### Your Team & Performance
```
"Show my current team and bank balance"
"How am I doing?"  → Automatically uses your entry
"What leagues am I in?"
"Show me my performance"
```

### Player Research (Use Names, Not IDs!)
```
"Find me the top midfielders by form"
"Compare Salah and Palmer"  → Just use player names!
"Is Haaland injured?"
"Show me Saka's upcoming fixtures"
"Tell me about Mohamed Salah"  → Fuzzy matching handles variations
```

### Competitive Analysis (Use Friendly Names!)
```
"Show me the standings for Greatest Fantasy Footy"  → Use league name!
"What team did Jaakko pick in gameweek 13?"  → Use manager name!
"Tell me about Lewis's team in Greatest Fantasy Footy"
"Compare Jaakko and Lewis in Greatest Fantasy Footy for gameweek 13"
"Who did the top managers in my league captain this week?"
```

### Team & Fixture Analysis (Use Team Names!)
```
"What are Arsenal's next 5 fixtures?"  → Just use team name!
"Show me Liverpool's fixture difficulty"
"Which teams have the best fixtures?"
"Show me all fixtures for gameweek 14"
```

### Strategic Planning
```
"Find players to avoid due to injuries"
"Is Salah available to play?"  → Check specific player
"Suggest transfers for next gameweek"
"Compare Haaland and Watkins"  → Direct name comparison
```

### Advanced Analysis
```
"Analyze why Jaakko is beating me in Greatest Fantasy Footy"
"Find differential picks in my league"
"Which premium midfielder has the best value?"
"Compare Arsenal and Man City players"
```

### 🔑 Key Principle: Names over IDs

```
"Show Greatest Fantasy Footy standings"
"What team did Jaakko pick?"
"Compare Salah and Palmer"
```

The system automatically:
- Fetches your entry ID after login
- Resolves league names from your leagues
- Finds managers by name within leagues
- Matches player names with fuzzy search
- Converts team names to IDs internally

## 🛠️ Available Tools

The server provides **30+ MCP tools** organized by category. All tools use **friendly names** instead of IDs!

### Authentication
- `login_to_fpl` - Generate secure login link
- `check_login_status` - Verify authentication and activate session

### Your Account
- `get_my_info` - View your account, entry, and leagues
- `get_my_squad` - View your current team
- `get_my_performance` - Your stats, ranks, and league positions
- `make_transfers` - Execute transfers using player names (irreversible!)

### Player Research (Use Player Names!)
- `search_players(name_query)` - Find players by name
- `find_player(player_name)` - Intelligent fuzzy search with full details
- `get_player_details(player_name)` - Detailed player info by name
- `get_player_summary(player_name)` - Comprehensive analysis with fixtures
- `compare_players(player_names)` - Side-by-side comparison using names
- `get_top_players()` - Best performers by position
- `search_players_by_team(team_name)` - Browse team squads by name

### Injury & Availability
- `get_injury_and_lineup_predictions()` - RotoWire lineup data
- `get_players_to_avoid()` - Injury risk assessment
- `check_player_availability(player_name)` - Check specific player status

### Fixtures & Teams (Use Team Names!)
- `get_fixtures_for_gameweek(gameweek)` - All matches in a gameweek
- `analyze_team_fixtures(team_name, num_gameweeks)` - Fixture difficulty by team name
- `get_team_info(team_name)` - Team strength ratings by name
- `list_all_teams()` - All Premier League teams

### Gameweek Information
- `get_current_gameweek()` - Current/upcoming gameweek
- `get_gameweek_info(gameweek_number)` - Detailed gameweek stats
- `list_all_gameweeks()` - Season overview

### Competitive Analysis (Use Friendly Names!)
- `get_league_standings(league_name, page)` - League rankings by league name
- `get_manager_gameweek_team(manager_name, league_name, gameweek)` - Inspect teams by manager name
- `compare_managers(manager_names, league_name, gameweek)` - Multi-manager comparison by names

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Claude Desktop                       │
│                    (Your AI Assistant)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    FPL MCP Server                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  MCP Tools   │  │  Data Cache  │  │  Auth System │     │
│  │  (30+ tools) │  │  (4hr TTL)   │  │  (Secure)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Fantasy Premier League API                      │
│  • Bootstrap Data  • Fixtures  • Player Stats               │
│  • Manager Data    • Leagues   • Gameweek Picks             │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **MCP Tools** - 30+ functions for FPL data access
- **Smart Caching** - 4-hour TTL for bootstrap/fixtures data
- **Player Rehydration** - Automatic ID-to-name conversion
- **Secure Auth** - Out-of-band login flow
- **RotoWire Integration** - Real-time injury updates

## 🔧 Troubleshooting

### Plug Icon Not Appearing

**Check Logs:**
* **Mac**: `tail -f ~/Library/Logs/Claude/mcp.log`
* **Windows**: Check `%APPDATA%\Claude\logs\mcp.log`

**Common Issues:**
- Did you run `uv sync` first?
- Is the `cwd` path in the JSON config correct (no typos)?
- Is `uv` in your system PATH?
- Try replacing `"command": "uv"` with the full path to your `uv` executable

### Authentication Issues

- Make sure you're using the correct FPL credentials
- Check that the web server is running on port 8000
- Try clearing browser cookies and logging in again

### Data Not Loading

- Check your internet connection
- Verify the FPL API is accessible
- Look for error messages in the logs
- Try restarting the Claude Desktop app

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Additional MCP tools for more FPL features
- Enhanced fixture difficulty algorithms
- Historical data analysis tools
- Transfer suggestion algorithms
- Price change predictions

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- Fantasy Premier League for API
- RotoWire for injury and lineup data
- The MCP community for the protocol
- Claude for AI capabilities

---

**Ready to dominate your FPL leagues with AI-powered insights? Get started now!** 🚀
