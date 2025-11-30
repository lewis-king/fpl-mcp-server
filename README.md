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

#### Circular Data Flow
The server enables **circular exploration** of FPL data:
```
Your Performance → Leagues → Standings → Competitor Teams → Player Analysis
     ↓                                           ↓
  Compare Teams ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

Example workflow:
1. "How am I doing in FPL?" → See your leagues
2. "Show league 899193 standings" → Find top competitors
3. "What team did entry 1734732 pick in GW13?" → Analyze their selections
4. "Compare my team to theirs" → Understand performance differences
5. "Tell me about Haaland's fixtures" → Research specific players

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

Quit Claude completely and reopen. Look for the 🔌 plug icon in the input bar.

## 💡 Usage Examples

### Getting Started
```
You: "Log me into FPL"
Claude: [Provides secure login link]
You: [Click link, enter credentials, confirm]
You: "I'm done"
Claude: "Authentication successful!"
```

### Your Team
```
"Show my current team and bank balance"
"What's my overall rank and points?"
"How am I doing in my leagues?"
```

### Player Research
```
"Find me the top midfielders by form"
"Compare Salah and Palmer"
"Is Haaland injured?"
"Show me Saka's upcoming fixtures"
"What are Arsenal's next 5 fixtures?"
```

### Competitive Analysis
```
"Show me the standings for league 899193"
"What team did entry 1734732 pick in gameweek 13?"
"Compare my team to the league leader's team"
"Who did the top 3 managers captain this week?"
```

### Strategic Planning
```
"Which teams have the best fixtures in the next 5 gameweeks?"
"Show me all fixtures for gameweek 14"
"Find players to avoid due to injuries"
"Suggest transfers for next gameweek"
```

### Advanced Analysis
```
"Analyze why the league leader is beating me"
"Find differential picks that top managers are using"
"Which premium midfielder has the best value?"
"Compare the fixture difficulty for Liverpool vs Man City assets"
```

## 🛠️ Available Tools

The server provides **30+ MCP tools** organized by category:

### Authentication
- `login_to_fpl` - Generate secure login link
- `check_login_status` - Verify authentication

### Team Management
- `get_my_squad` - View current team
- `make_transfers` - Execute transfers (irreversible!)
- `get_my_fpl_performance` - Your stats and rankings

### Player Research
- `search_players` - Find players by name
- `find_player` - Intelligent fuzzy search
- `get_player_details` - Detailed player info
- `get_player_summary` - Comprehensive analysis with fixtures
- `compare_players` - Side-by-side comparison
- `get_top_players` - Best performers by position
- `search_players_by_team` - Team squad browser

### Injury & Availability
- `get_injury_and_lineup_predictions` - RotoWire lineup data
- `get_players_to_avoid` - Injury risk assessment
- `check_player_availability` - Individual player status

### Fixtures & Teams
- `get_fixtures_for_gameweek` - All matches in a gameweek
- `analyze_team_fixtures` - Fixture difficulty analysis
- `get_team_info` - Team strength ratings
- `list_all_teams` - All Premier League teams

### Gameweek Information
- `get_current_gameweek` - Current/upcoming gameweek
- `get_gameweek_info` - Detailed gameweek stats
- `list_all_gameweeks` - Season overview

### Competitive Analysis
- `get_league_standings` - League rankings
- `get_manager_gameweek_team` - Inspect competitor teams
- `compare_managers` - Multi-manager comparison

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

- Fantasy Premier League for the excellent API
- RotoWire for injury and lineup data
- The MCP community for the protocol
- Claude for AI capabilities

---

**Ready to dominate your FPL leagues with AI-powered insights? Get started now!** 🚀