import httpx
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from .models import Player, TransferPayload, BootstrapData

if TYPE_CHECKING:
    from .state import SessionStore

logger = logging.getLogger("fpl_client")

class FPLClient:
    BASE_URL = "https://fantasy.premierleague.com/api/"
    
    def __init__(self, store: Optional['SessionStore'] = None):
        self.session = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30.0
        )
        self.api_token = None
        self.team_id: Optional[int] = None
        self._store = store

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
        """Fetch fresh bootstrap data from API (used for events/gameweeks)"""
        return await self._request("GET", "bootstrap-static/")

    async def get_players(self) -> List[Player]:
        """Get all players using cached bootstrap data"""
        # Use cached data if available
        if self._store and self._store.bootstrap_data:
            data = self._store.bootstrap_data
            teams = {t.id: t.name for t in data.teams}
            types = {t.id: t.singular_name_short for t in data.element_types}
            
            players = []
            for element in data.elements:
                # Convert ElementData to Player
                player = Player(
                    id=element.id,
                    web_name=element.web_name,
                    first_name=element.first_name,
                    second_name=element.second_name,
                    team=element.team,
                    element_type=element.element_type,
                    now_cost=element.now_cost,
                    form=element.form,
                    points_per_game=element.points_per_game,
                    news=element.news
                )
                player.team_name = teams.get(player.team, "Unknown")
                player.position = types.get(player.element_type, "Unk")
                players.append(player)
            return players
        
        # Fallback to API if cached data not available
        logger.warning("Bootstrap data not cached, fetching from API")
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

    async def get_top_players_by_position(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get top players by position based on points per game.
        Returns: {
            'GKP': [top 5 goalkeepers],
            'DEF': [top 20 defenders],
            'MID': [top 20 midfielders],
            'FWD': [top 20 forwards]
        }
        """
        if not self._store or not self._store.bootstrap_data:
            logger.warning("Bootstrap data not available for top players")
            return {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
        
        data = self._store.bootstrap_data
        teams = {t.id: t.name for t in data.teams}
        types = {t.id: t.singular_name_short for t in data.element_types}
        
        # Group players by position
        players_by_position = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
        
        for element in data.elements:
            # Only include available players
            if element.status != 'a':
                continue
                
            position = types.get(element.element_type, 'UNK')
            if position not in players_by_position:
                continue
            
            # Convert to float for sorting, handle 0.0 as string
            try:
                ppg = float(element.points_per_game) if element.points_per_game else 0.0
            except ValueError:
                ppg = 0.0
            
            player_data = {
                'id': element.id,
                'name': element.web_name,
                'full_name': f"{element.first_name} {element.second_name}",
                'team': teams.get(element.team, 'Unknown'),
                'price': element.now_cost / 10,
                'points_per_game': ppg,
                'total_points': getattr(element, 'total_points', 0),
                'form': element.form,
                'status': element.status,
                'news': element.news if element.news else ''
            }
            players_by_position[position].append(player_data)
        
        # Sort by points_per_game and take top N
        result = {
            'GKP': sorted(players_by_position['GKP'], key=lambda x: x['points_per_game'], reverse=True)[:5],
            'DEF': sorted(players_by_position['DEF'], key=lambda x: x['points_per_game'], reverse=True)[:20],
            'MID': sorted(players_by_position['MID'], key=lambda x: x['points_per_game'], reverse=True)[:20],
            'FWD': sorted(players_by_position['FWD'], key=lambda x: x['points_per_game'], reverse=True)[:20]
        }
        
        return result

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