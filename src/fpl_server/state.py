from typing import Dict, Optional
from dataclasses import dataclass
import time
from .client import FPLClient

@dataclass
class PendingLogin:
    created_at: float
    status: str = "pending"  # pending, success, failed
    session_id: Optional[str] = None
    error: Optional[str] = None

class SessionStore:
    def __init__(self):
        # Maps request_id (from URL) -> Login Status
        self.pending_logins: Dict[str, PendingLogin] = {}
        
        # Maps session_id (given to LLM) -> Authenticated FPLClient
        self.active_sessions: Dict[str, FPLClient] = {}

    def create_login_request(self, request_id: str):
        self.pending_logins[request_id] = PendingLogin(created_at=time.time())

    def set_login_success(self, request_id: str, session_id: str, client: FPLClient):
        self.active_sessions[session_id] = client
        if request_id in self.pending_logins:
            self.pending_logins[request_id].status = "success"
            self.pending_logins[request_id].session_id = session_id

    def set_login_failure(self, request_id: str, error: str):
        if request_id in self.pending_logins:
            self.pending_logins[request_id].status = "failed"
            self.pending_logins[request_id].error = error

    def get_client(self, session_id: str) -> Optional[FPLClient]:
        return self.active_sessions.get(session_id)

# Global Instance
store = SessionStore()