import httpx
import logging
from typing import Any, Dict, List, Optional
from .models import Player, TransferPayload

logger = logging.getLogger("fpl_client")

class FPLClient:
    BASE_URL = "https://fantasy.premierleague.com/api/"
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30.0
        )
        self.api_token = None
        self.team_id: Optional[int] = None

    def set_api_token(self, token: str):
        if not token.startswith("Bearer "):
            token = f"Bearer {token}"
        self.api_token = token
        
    async def _request(self, method: str, endpoint: str, data: dict = None) -> Any:
        url = f"{self.BASE_URL}{endpoint}"
        headers = {}
        if self.api_token:
            headers['x-api-authorization'] = self.api_token
            headers['Authorization'] = self.api_token 

        if method == "GET":
            response = await self.session.get(url, headers=headers)
        else:
            response = await self.session.post(url, json=data, headers=headers)
        
        response.raise_for_status()
        return response.json()

    async def get_bootstrap_data(self) -> Dict[str, Any]:
        return await self._request("GET", "bootstrap-static/")

    async def get_players(self) -> List[Player]:
        data = await self.get_bootstrap_data()
        teams = {t['id']: t['name'] for t in data['teams']}
        types = {t['id']: t['singular_name_short'] for t in data['element_types']}
        
        players = []
        for p in data['elements']:
            player = Player(**p)
            player.team_name = teams.get(player.team, "Unknown")
            player.position = types.get(player.element_type, "Unk")
            players.append(player)
        return players

    async def get_my_team(self, team_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"my-team/{team_id}/")

    async def get_current_gameweek(self) -> int:
        data = await self.get_bootstrap_data()
        for event in data['events']:
            if event['is_next']:
                return event['id']
        return 38

    async def execute_transfers(self, payload: TransferPayload) -> Dict[str, Any]:
        return await self._request("POST", "transfers/", payload.model_dump())
        
    async def close(self):
        await self.session.aclose()