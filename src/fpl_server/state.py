from typing import Dict, Optional
from dataclasses import dataclass
import time
import json
import logging
from pathlib import Path
from .client import FPLClient
from .models import BootstrapData

logger = logging.getLogger("fpl_state")

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
        
        # Cached bootstrap data loaded at startup
        self.bootstrap_data: Optional[BootstrapData] = None
        self._load_bootstrap_data()

    def _load_bootstrap_data(self):
        """Load bootstrap data from local JSON file"""
        try:
            # Find the data file relative to this module
            current_dir = Path(__file__).parent.parent.parent
            data_path = current_dir / "data" / "bootsrap_data.json"
            
            if not data_path.exists():
                logger.warning(f"Bootstrap data file not found at {data_path}")
                return
            
            with open(data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            self.bootstrap_data = BootstrapData(**raw_data)
            logger.info(f"Loaded {len(self.bootstrap_data.elements)} players from local bootstrap data")
        except Exception as e:
            logger.error(f"Failed to load bootstrap data: {e}")
            self.bootstrap_data = None

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