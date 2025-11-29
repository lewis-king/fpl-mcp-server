import sys
import traceback

# 1. Log immediately to prove Python started
sys.stderr.write("DEBUG: Python process started. Attempting imports...\n")
sys.stderr.flush()

try:
    import threading
    import uvicorn
    from .web import app
    from .mcp_tools import mcp
    sys.stderr.write("DEBUG: Imports successful.\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"CRITICAL IMPORT ERROR: {e}\n")
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

def run_web_server():
    try:
        sys.stderr.write("DEBUG: Starting Uvicorn on port 8000...\n")
        sys.stderr.flush()
        # log_level="critical" is even quieter than "error"
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="critical")
    except Exception as e:
        sys.stderr.write(f"WEB SERVER ERROR: {e}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()

def main():
    try:
        sys.stderr.write("DEBUG: Starting Web Thread...\n")
        sys.stderr.flush()
        
        # Start FastAPI in a background thread
        t = threading.Thread(target=run_web_server, daemon=True)
        t.start()
        
        # Start MCP Server on main thread (Stdio)
        sys.stderr.write("DEBUG: Starting MCP Server (Stdio)... Waiting for input.\n")
        sys.stderr.flush()
        
        # This function blocks and waits for Claude to send JSON
        mcp.run(transport='stdio')
        
        sys.stderr.write("DEBUG: MCP Server stopped normally.\n")
        sys.stderr.flush()
        
    except Exception as e:
        sys.stderr.write(f"MAIN RUNTIME ERROR: {e}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()

if __name__ == "__main__":
    main()