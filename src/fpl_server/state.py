from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import time
import json
import logging
import asyncio
from pathlib import Path
from difflib import SequenceMatcher
from .client import FPLClient
from .models import BootstrapData, ElementData, EventData, FixtureData
from .cache import DataCache

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
        
        # Cached fixtures data
        self.fixtures_data: Optional[List[FixtureData]] = None
        
        # Player name lookup maps for intelligent searching
        # Maps normalized name -> list of player IDs (handles duplicates)
        self.player_name_map: Dict[str, List[int]] = {}
        self.player_id_map: Dict[int, ElementData] = {}
        
        # Cache manager with 4-hour TTL
        self.cache = DataCache(cache_dir="data", ttl_hours=4)
        
        self._load_bootstrap_data()
        self._load_fixtures_data()

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for matching: lowercase, remove extra spaces"""
        return " ".join(name.lower().strip().split())
    
    def _load_bootstrap_data(self):
        """Load bootstrap data from cache or fetch from API if expired"""
        try:
            # Always try to load from cache first (even if expired)
            raw_data = self.cache.get("bootstrap_data.json", ignore_expiry=True)
            if raw_data:
                self.bootstrap_data = BootstrapData(**raw_data)
                self._build_player_indices()
                cache_info = self.cache.get_cache_info('bootstrap_data.json')
                logger.info(
                    f"Loaded {len(self.bootstrap_data.elements)} players from cache. "
                    f"Cache info: {cache_info}"
                )
                
                # If cache is expired, log a warning but continue using it
                if self.cache.is_expired("bootstrap_data.json"):
                    logger.warning("Bootstrap cache is expired but will be used. Consider refreshing.")
                
                return
            
            # No cache available at all - this is a problem
            logger.error("No bootstrap cache found. Please run the server to populate cache.")
            self.bootstrap_data = None
                
        except Exception as e:
            logger.error(f"Failed to load bootstrap data: {e}")
            self.bootstrap_data = None
    
    def _build_player_indices(self):
        """Build player name and ID indices from bootstrap data"""
        if not self.bootstrap_data:
            return
        
        # Enrich elements with team names for faster lookups
        team_map = {t.id: t.name for t in self.bootstrap_data.teams}
        position_map = {t.id: t.singular_name_short for t in self.bootstrap_data.element_types}
        
        # Build player name index and ID map
        self.player_name_map.clear()
        self.player_id_map.clear()
        
        for element in self.bootstrap_data.elements:
            # Add team_name and position to each element
            element.team_name = team_map.get(element.team, "Unknown")
            element.position = position_map.get(element.element_type, "UNK")
            
            # Store in ID map
            self.player_id_map[element.id] = element
            
            # Build name index with multiple keys for flexible matching
            # 1. Web name (most common)
            web_key = self._normalize_name(element.web_name)
            if web_key not in self.player_name_map:
                self.player_name_map[web_key] = []
            self.player_name_map[web_key].append(element.id)
            
            # 2. Full name (first + second)
            full_key = self._normalize_name(f"{element.first_name} {element.second_name}")
            if full_key not in self.player_name_map:
                self.player_name_map[full_key] = []
            if element.id not in self.player_name_map[full_key]:
                self.player_name_map[full_key].append(element.id)
            
            # 3. Second name only (surname)
            surname_key = self._normalize_name(element.second_name)
            if surname_key not in self.player_name_map:
                self.player_name_map[surname_key] = []
            if element.id not in self.player_name_map[surname_key]:
                self.player_name_map[surname_key].append(element.id)
            
            # 4. First name + web name (for cases like "Mohamed Salah")
            if element.first_name and element.web_name != element.second_name:
                first_web_key = self._normalize_name(f"{element.first_name} {element.web_name}")
                if first_web_key not in self.player_name_map:
                    self.player_name_map[first_web_key] = []
                if element.id not in self.player_name_map[first_web_key]:
                    self.player_name_map[first_web_key].append(element.id)
        
        logger.info(
            f"Loaded {len(self.bootstrap_data.elements)} players, "
            f"{len(self.bootstrap_data.teams)} teams, "
            f"{len(self.bootstrap_data.events)} gameweeks. "
            f"Built name index with {len(self.player_name_map)} keys."
        )
    
    def _load_fixtures_data(self):
        """Load fixtures data from cache or fetch from API if expired"""
        try:
            # Always try to load from cache first (even if expired)
            raw_data = self.cache.get("fixtures.json", ignore_expiry=True)
            if raw_data:
                self.fixtures_data = [FixtureData(**fixture) for fixture in raw_data]
                cache_info = self.cache.get_cache_info('fixtures.json')
                logger.info(
                    f"Loaded {len(self.fixtures_data)} fixtures from cache. "
                    f"Cache info: {cache_info}"
                )
                
                # If cache is expired, log a warning but continue using it
                if self.cache.is_expired("fixtures.json"):
                    logger.warning("Fixtures cache is expired but will be used. Consider refreshing.")
                
                return
            
            # No cache available at all - this is a problem
            logger.error("No fixtures cache found. Please run the server to populate cache.")
            self.fixtures_data = None
                
        except Exception as e:
            logger.error(f"Failed to load fixtures data: {e}")
            self.fixtures_data = None

    def create_login_request(self, request_id: str):
        self.pending_logins[request_id] = PendingLogin(created_at=time.time())

    async def set_login_success(self, request_id: str, session_id: str, client: FPLClient):
        """Set login success and fetch user info from /me endpoint"""
        self.active_sessions[session_id] = client
        
        # Fetch user info after successful login and store it in the client
        try:
            user_data = await client.get_me()
            client.user_info = user_data  # Store the user info in the client
            entry_id = user_data.get('player', {}).get('entry')
            logger.info(f"Fetched and stored user info for session {session_id}: entry_id={entry_id}")
        except Exception as e:
            logger.error(f"Failed to fetch user info after login: {e}")
        
        if request_id in self.pending_logins:
            self.pending_logins[request_id].status = "success"
            self.pending_logins[request_id].session_id = session_id

    def set_login_failure(self, request_id: str, error: str):
        if request_id in self.pending_logins:
            self.pending_logins[request_id].status = "failed"
            self.pending_logins[request_id].error = error

    def get_client(self, session_id: str) -> Optional[FPLClient]:
        return self.active_sessions.get(session_id)
    
    def get_team_by_id(self, team_id: int) -> Optional[dict]:
        """Get team information by ID"""
        if not self.bootstrap_data:
            return None
        
        team = next((t for t in self.bootstrap_data.teams if t.id == team_id), None)
        if not team:
            return None
        
        return {
            'id': team.id,
            'name': team.name,
            'short_name': team.short_name,
            'strength': getattr(team, 'strength', None),
            'strength_overall_home': getattr(team, 'strength_overall_home', None),
            'strength_overall_away': getattr(team, 'strength_overall_away', None),
            'strength_attack_home': getattr(team, 'strength_attack_home', None),
            'strength_attack_away': getattr(team, 'strength_attack_away', None),
            'strength_defence_home': getattr(team, 'strength_defence_home', None),
            'strength_defence_away': getattr(team, 'strength_defence_away', None),
        }
    
    def get_all_teams(self) -> list:
        """Get all teams with their information"""
        if not self.bootstrap_data:
            return []
        
        return [
            {
                'id': t.id,
                'name': t.name,
                'short_name': t.short_name,
                'strength': getattr(t, 'strength', None),
                'strength_overall_home': getattr(t, 'strength_overall_home', None),
                'strength_overall_away': getattr(t, 'strength_overall_away', None),
            }
            for t in self.bootstrap_data.teams
        ]
    
    def find_players_by_name(self, name_query: str, fuzzy: bool = True) -> List[Tuple[ElementData, float]]:
        """
        Find players by name with intelligent matching.
        Returns list of (player, similarity_score) tuples sorted by relevance.
        
        Args:
            name_query: The name to search for
            fuzzy: Whether to use fuzzy matching for close matches
        
        Returns:
            List of (ElementData, similarity_score) tuples, sorted by score descending
        """
        if not self.bootstrap_data:
            return []
        
        normalized_query = self._normalize_name(name_query)
        results: Dict[int, float] = {}  # player_id -> best similarity score
        
        # 1. Exact match
        if normalized_query in self.player_name_map:
            for player_id in self.player_name_map[normalized_query]:
                results[player_id] = 1.0
        
        # 2. Substring match (contains)
        if not results:
            for name_key, player_ids in self.player_name_map.items():
                if normalized_query in name_key or name_key in normalized_query:
                    # Calculate similarity based on length ratio
                    similarity = min(len(normalized_query), len(name_key)) / max(len(normalized_query), len(name_key))
                    for player_id in player_ids:
                        if player_id not in results or similarity > results[player_id]:
                            results[player_id] = similarity * 0.9  # Slightly lower than exact
        
        # 3. Fuzzy matching (if enabled and no good matches yet)
        if fuzzy and (not results or max(results.values()) < 0.7):
            for name_key, player_ids in self.player_name_map.items():
                similarity = SequenceMatcher(None, normalized_query, name_key).ratio()
                if similarity >= 0.6:  # Threshold for fuzzy matches
                    for player_id in player_ids:
                        if player_id not in results or similarity > results[player_id]:
                            results[player_id] = similarity * 0.8  # Lower than substring
        
        # Convert to list of tuples and sort by score
        player_matches = [
            (self.player_id_map[player_id], score)
            for player_id, score in results.items()
        ]
        player_matches.sort(key=lambda x: x[1], reverse=True)
        
        return player_matches
    
    def get_player_by_id(self, player_id: int) -> Optional[ElementData]:
        """Get a player by their ID"""
        return self.player_id_map.get(player_id)
    
    def get_current_gameweek(self) -> Optional[EventData]:
        """Get the current gameweek event"""
        if not self.bootstrap_data or not self.bootstrap_data.events:
            return None
        
        # First check for is_current flag
        for event in self.bootstrap_data.events:
            if event.is_current:
                return event
        
        # Fallback to is_next if current deadline has passed
        for event in self.bootstrap_data.events:
            if event.is_next:
                return event
        
        # Last resort: first unfinished gameweek
        for event in self.bootstrap_data.events:
            if not event.finished:
                return event
        
        return None
    
    def rehydrate_player_names(self, element_ids: list[int]) -> dict[int, dict]:
        """
        Rehydrate player element IDs to full player information.
        
        Args:
            element_ids: List of player element IDs
            
        Returns:
            Dictionary mapping element_id -> player info dict
        """
        result = {}
        for element_id in element_ids:
            player = self.get_player_by_id(element_id)
            if player:
                result[element_id] = {
                    'id': player.id,
                    'web_name': player.web_name,
                    'full_name': f"{player.first_name} {player.second_name}",
                    'team': player.team_name,
                    'position': player.position,
                    'price': player.now_cost / 10,
                    'form': player.form,
                    'points_per_game': player.points_per_game,
                    'total_points': getattr(player, 'total_points', 0),
                    'status': player.status,
                    'news': player.news
                }
        return result
    
    def get_player_name(self, element_id: int) -> str:
        """
        Get a player's web name by their element ID.
        
        Args:
            element_id: The player's element ID
            
        Returns:
            Player's web name or "Unknown Player (ID: {element_id})"
        """
        player = self.get_player_by_id(element_id)
        if player:
            return player.web_name
        return f"Unknown Player (ID: {element_id})"
    
    async def find_league_by_name(self, client: FPLClient, league_name: str) -> Optional[dict]:
        """
        Find a league by name from the user's leagues.
        
        Args:
            client: The authenticated FPL client
            league_name: The name of the league to find
            
        Returns:
            League dict with 'id' and 'name' if found, None otherwise
        """
        if not client.user_info:
            return None
        
        # Get all leagues the user is in
        classic_leagues = client.user_info.get('leagues', {}).get('classic', [])
        
        # Normalize search name
        normalized_search = self._normalize_name(league_name)
        
        # Try exact match first
        for league in classic_leagues:
            if self._normalize_name(league.get('name', '')) == normalized_search:
                return {
                    'id': league.get('id'),
                    'name': league.get('name')
                }
        
        # Try substring match
        for league in classic_leagues:
            league_norm = self._normalize_name(league.get('name', ''))
            if normalized_search in league_norm or league_norm in normalized_search:
                return {
                    'id': league.get('id'),
                    'name': league.get('name')
                }
        
        return None
    
    async def find_manager_by_name(self, client: FPLClient, league_id: int, manager_name: str) -> Optional[dict]:
        """
        Find a manager by name in a league's standings.
        
        Args:
            client: The authenticated FPL client
            league_id: The league ID to search in
            manager_name: The manager's name to find
            
        Returns:
            Manager dict with 'entry', 'entry_name', 'player_name' if found, None otherwise
        """
        try:
            standings = await client.get_league_standings(league_id)
            
            # Normalize search name
            normalized_search = self._normalize_name(manager_name)
            
            # Search through standings
            for result in standings.standings.results:
                # Try matching against player_name (manager name)
                if self._normalize_name(result.player_name) == normalized_search:
                    return {
                        'entry': result.entry,
                        'entry_name': result.entry_name,
                        'player_name': result.player_name
                    }
                
                # Try matching against entry_name (team name)
                if self._normalize_name(result.entry_name) == normalized_search:
                    return {
                        'entry': result.entry,
                        'entry_name': result.entry_name,
                        'player_name': result.player_name
                    }
            
            # Try substring matches
            for result in standings.standings.results:
                player_norm = self._normalize_name(result.player_name)
                entry_norm = self._normalize_name(result.entry_name)
                
                if (normalized_search in player_norm or player_norm in normalized_search or
                    normalized_search in entry_norm or entry_norm in normalized_search):
                    return {
                        'entry': result.entry,
                        'entry_name': result.entry_name,
                        'player_name': result.player_name
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding manager by name: {e}")
            return None
    
    def get_user_entry_id(self, client: FPLClient) -> Optional[int]:
        """
        Get the user's entry ID from their stored user info.
        
        Args:
            client: The authenticated FPL client
            
        Returns:
            The user's entry ID or None if not available
        """
        if not client.user_info:
            return None
        return client.user_info.get('player', {}).get('entry')

# Global Instance
store = SessionStore()