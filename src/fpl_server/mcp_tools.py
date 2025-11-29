import uuid
from mcp.server.fastmcp import FastMCP
from .state import store
from .models import TransferPayload

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