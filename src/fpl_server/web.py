import uuid
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from .auth import FPLAutomation
from .client import FPLClient
from .state import store

app = FastAPI()

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FPL MCP Login</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #37003c; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .container { background: white; color: #333; padding: 2rem; border-radius: 12px; width: 100%; max-width: 320px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h2 { color: #37003c; margin-top: 0; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #00ff87; color: #37003c; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button:hover { opacity: 0.9; }
        .note { font-size: 0.8em; color: #666; margin-top: 15px; text-align: center; }
        .loader { display: none; text-align: center; margin-top: 15px; font-weight: bold; color: #37003c; }
    </style>
    <script>
        function showLoader() {
            document.querySelector('.loader').style.display = 'block';
            document.querySelector('button').disabled = true;
            document.querySelector('button').innerText = 'Authenticating...';
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>FPL Connection</h2>
        <p>Enter your credentials to connect your FPL account to the AI Assistant.</p>
        <form action="/auth/submit/{request_id}" method="post" onsubmit="showLoader()">
            <input type="text" name="team_id" placeholder="FPL Team ID (e.g., 123456)" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Secure Login</button>
        </form>
        <div class="loader">
            Connecting to FPL...<br>Please wait approx 10-15 seconds.
        </div>
        <div class="note">Your credentials are processed locally and used only to acquire a session token.</div>
    </div>
</body>
</html>
"""

@app.get("/login/{request_id}", response_class=HTMLResponse)
async def login_page(request_id: str):
    store.create_login_request(request_id)
    return LOGIN_HTML.replace("{request_id}", request_id)

@app.post("/auth/submit/{request_id}")
async def submit_login(request_id: str, email: str = Form(...), password: str = Form(...), team_id: int = Form(...)):
    try:
        auth = FPLAutomation(email, password)
        token = await auth.login_and_get_token()
        
        if token:
            session_id = str(uuid.uuid4())
            client = FPLClient()
            client.set_api_token(token)
            client.team_id = team_id
            
            store.set_login_success(request_id, session_id, client)
            return HTMLResponse("""
                <body style="background:#00ff87; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif;">
                    <div style="background:white; padding:2rem; border-radius:10px; text-align:center;">
                        <h1 style="color:#37003c;">Connected!</h1>
                        <p>You can now close this tab and return to the chat.</p>
                    </div>
                </body>
            """)
        else:
            store.set_login_failure(request_id, "Could not capture token")
            return HTMLResponse("<body><h1>Login Failed</h1><p>Could not capture token from FPL.</p></body>")
            
    except Exception as e:
        store.set_login_failure(request_id, str(e))
        return HTMLResponse(f"<body><h1>Error</h1><p>{str(e)}</p></body>")