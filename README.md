# FPL MCP Server

Control your Fantasy Premier League team with your favourite LLM to help inform your decisions and gain more contextual insights based on your team

A secure, multi-user Model Context Protocol (MCP) server for Fantasy Premier League.

This server enables LLMs (like Claude) to interact with your FPL squad securely. It uses an "Out-of-Band" authentication flow where credentials are entered into a local web form, meaning your password is **never** shared with the LLM.

## Prerequisites

1.  **Install `uv`** (An extremely fast Python package manager):
    * **Mac/Linux**:
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```
    * **Windows**:
        ```powershell
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```

## 1. Installation & Setup

1.  **Verify Directory Structure**:
    Ensure your project folder looks like this:
    ```text
    fpl-mcp-server/
    ├── pyproject.toml
    ├── README.md
    └── src/
        └── fpl_server/
            ├── __init__.py
            ├── main.py
            ├── web.py
            ├── mcp_tools.py
            ├── auth.py
            ├── client.py
            ├── models.py
            └── state.py
    ```

2.  **Install Dependencies**:
    Run this command in the root folder. It will create a virtual environment (`.venv`) and install all required packages defined in `pyproject.toml`.
    ```bash
    uv sync
    ```

3.  **Install Playwright Browsers**:
    This is required for the login automation to work.
    ```bash
    uv run playwright install chromium
    ```

## 2. Testing Locally (Optional)

Before connecting to Claude, you can verify the server starts up correctly:

```bash
uv run --env PYTHONPATH=src python -m fpl_server.main
```

You should see output similar to:

```text
Starting FPL Web Auth on http://localhost:8000
Starting MCP Server (Stdio)...
```

Press `Ctrl+C` to stop the server.

## 3. Connect to Claude Desktop

To use this with the Claude Desktop App, you need to configure it to run your server.

### Get your Project Path

* **Mac/Linux**: Run `pwd` in your terminal inside the project folder.
* **Windows**: Run `cd` in your terminal inside the project folder.

Copy this full absolute path.

### Open Claude Config

Open this file in any text editor (VS Code, Notepad, etc.):

* **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Update the Config

Add the `fpl` server to your `mcpServers` list.
**CRITICAL**: Replace `/ABSOLUTE/PATH/TO/fpl-mcp-server` with the actual path you copied in Step 1.

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

### Restart Claude Desktop

Quit the application completely (don't just close the window) and reopen it. Look for the 🔌 plug icon in the input bar.

## 4. Usage Flow

Once connected, here is how you interact with it:

1.  **Open Claude Desktop.**
2.  **Ask**: "Log me into FPL."
3.  **Claude**: Will provide a secure local link (e.g., `http://localhost:8000/login/...`).
4.  **Action**: Click the link -> Enter FPL Credentials -> Click Login.
5.  **Wait**: Wait for the green "Connected!" screen in your browser.
6.  **Action**: Close the browser tab and tell Claude: "I'm done."
7.  **Claude**: Will confirm authentication.
8.  **Manage**: You can now ask things like:
    * "Show my team and bank balance"
    * "Suggest transfers for next gameweek"
    * "Swap Salah for Palmer"

## 5. Troubleshooting

If the plug icon doesn't appear or shows a red dot:

### Check Logs

* **Mac**: `tail -f ~/Library/Logs/Claude/mcp.log`
* **Windows**: Check `%APPDATA%\Claude\logs\mcp.log`

### Common Issues

* Did you run `uv sync` first?
* Is the `cwd` path in the JSON config correct (no typos)?
* Is `uv` in your system PATH? (You can try replacing `"command": "uv"` with the full path to your `uv` executable).