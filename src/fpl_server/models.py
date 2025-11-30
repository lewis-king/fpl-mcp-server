from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Player(BaseModel):
    id: int
    web_name: str
    first_name: str
    second_name: str
    team: int
    element_type: int
    now_cost: int
    form: str
    points_per_game: str
    news: str
    
    # Computed fields
    team_name: Optional[str] = None
    position: Optional[str] = None
    price: float = Field(default=0.0)

    def __init__(self, **data):
        super().__init__(**data)
        self.price = self.now_cost / 10

class ElementData(BaseModel):
    """Player element from bootstrap data"""
    id: int
    web_name: str
    first_name: str
    second_name: str
    team: int
    element_type: int
    now_cost: int
    form: str
    points_per_game: str
    news: str
    status: str
    
    # Enriched fields (added during bootstrap loading)
    team_name: Optional[str] = None
    position: Optional[str] = None
    
    # Allow extra fields from the API that we don't need to validate
    class Config:
        extra = "allow"

class TeamData(BaseModel):
    """Team data from bootstrap"""
    id: int
    name: str
    short_name: str
    class Config:
        extra = "allow"

class ElementTypeData(BaseModel):
    """Position type data from bootstrap"""
    id: int
    singular_name_short: str
    plural_name_short: str
    class Config:
        extra = "allow"

class TopElementInfo(BaseModel):
    """Top scoring player info for an event"""
    id: int
    points: int

class EventData(BaseModel):
    """Gameweek event data from bootstrap"""
    id: int
    name: str
    deadline_time: str
    average_entry_score: Optional[int] = None
    finished: bool
    data_checked: bool
    highest_scoring_entry: Optional[int] = None
    deadline_time_epoch: int
    highest_score: Optional[int] = None
    is_previous: bool
    is_current: bool
    is_next: bool
    can_enter: bool
    released: bool
    top_element: Optional[int] = None
    top_element_info: Optional[TopElementInfo] = None
    most_selected: Optional[int] = None
    most_transferred_in: Optional[int] = None
    most_captained: Optional[int] = None
    most_vice_captained: Optional[int] = None
    
    class Config:
        extra = "allow"

class BootstrapData(BaseModel):
    """Bootstrap static data structure"""
    elements: List[ElementData]
    teams: List[TeamData]
    element_types: List[ElementTypeData]
    events: List[EventData]
    class Config:
        extra = "allow"

class TransferPayload(BaseModel):
    chip: Optional[str] = None
    entry: int
    event: int
    transfers: List[Dict[str, int]]
    wildcard: bool = False
    freehit: bool = False

class FixtureStatValue(BaseModel):
    """Individual stat value in a fixture"""
    value: int
    element: int

class FixtureStat(BaseModel):
    """Stat category in a fixture"""
    identifier: str
    a: List[FixtureStatValue]
    h: List[FixtureStatValue]

class FixtureData(BaseModel):
    """Fixture data from the fixtures endpoint"""
    code: int
    event: Optional[int] = None
    finished: bool
    finished_provisional: bool
    id: int
    kickoff_time: Optional[str] = None
    minutes: int
    provisional_start_time: bool
    started: bool
    team_a: int
    team_a_score: Optional[int] = None
    team_h: int
    team_h_score: Optional[int] = None
    stats: List[FixtureStat]
    team_h_difficulty: int
    team_a_difficulty: int
    pulse_id: int
    
    class Config:
        extra = "allow"

# Models for element-summary endpoint (player details)

class PlayerFixture(BaseModel):
    """Fixture information for a player"""
    id: int
    code: int
    team_h: int
    team_h_score: Optional[int] = None
    team_a: int
    team_a_score: Optional[int] = None
    event: Optional[int] = None
    finished: bool
    minutes: int
    provisional_start_time: bool
    kickoff_time: Optional[str] = None
    event_name: str
    is_home: bool
    difficulty: int

class PlayerHistory(BaseModel):
    """Historical performance data for a player in a gameweek"""
    element: int
    fixture: int
    opponent_team: int
    total_points: int
    was_home: bool
    kickoff_time: str
    team_h_score: Optional[int] = None
    team_a_score: Optional[int] = None
    round: int
    modified: bool
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    bonus: int
    bps: int
    influence: str
    creativity: str
    threat: str
    ict_index: str
    starts: int
    expected_goals: str
    expected_assists: str
    expected_goal_involvements: str
    expected_goals_conceded: str
    value: int
    transfers_balance: int
    selected: int
    transfers_in: int
    transfers_out: int
    
    class Config:
        extra = "allow"

class PlayerHistoryPast(BaseModel):
    """Historical season data for a player"""
    season_name: str
    element_code: int
    start_cost: int
    end_cost: int
    total_points: int
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    bonus: int
    bps: int
    influence: str
    creativity: str
    threat: str
    ict_index: str
    starts: int
    expected_goals: str
    expected_assists: str
    expected_goal_involvements: str
    expected_goals_conceded: str
    
    class Config:
        extra = "allow"

class ElementSummary(BaseModel):
    """Complete player summary from element-summary endpoint"""
    fixtures: List[PlayerFixture]
    history: List[PlayerHistory]
    history_past: List[PlayerHistoryPast]

# Models for entry endpoint (FPL manager/team info)

class LeaguePhase(BaseModel):
    """Phase information within a league"""
    phase: int
    rank: int
    last_rank: int
    rank_sort: int
    total: int
    league_id: int
    rank_count: Optional[int] = None
    entry_percentile_rank: Optional[int] = None

class ClassicLeague(BaseModel):
    """Classic league information for a manager"""
    id: int
    name: str
    short_name: Optional[str] = None
    created: str
    closed: bool
    rank: Optional[int] = None
    max_entries: Optional[int] = None
    league_type: str
    scoring: str
    admin_entry: Optional[int] = None
    start_event: int
    entry_can_leave: bool
    entry_can_admin: bool
    entry_can_invite: bool
    has_cup: bool
    cup_league: Optional[int] = None
    cup_qualified: Optional[bool] = None
    rank_count: Optional[int] = None
    entry_percentile_rank: Optional[int] = None
    active_phases: List[LeaguePhase]
    entry_rank: int
    entry_last_rank: int

class CupStatus(BaseModel):
    """Cup qualification status"""
    qualification_event: Optional[int] = None
    qualification_numbers: Optional[int] = None
    qualification_rank: Optional[int] = None
    qualification_state: Optional[str] = None

class Cup(BaseModel):
    """Cup information for a manager"""
    matches: List[Any]
    status: CupStatus
    cup_league: Optional[int] = None

class Leagues(BaseModel):
    """All leagues information for a manager"""
    classic: List[ClassicLeague]
    h2h: List[Any]
    cup: Cup
    cup_matches: List[Any]

class ManagerEntry(BaseModel):
    """FPL manager/team entry information"""
    id: int
    joined_time: str
    started_event: int
    favourite_team: Optional[int] = None
    player_first_name: str
    player_last_name: str
    player_region_id: int
    player_region_name: str
    player_region_iso_code_short: str
    player_region_iso_code_long: str
    years_active: int
    summary_overall_points: int
    summary_overall_rank: int
    summary_event_points: int
    summary_event_rank: int
    current_event: int
    leagues: Leagues
    name: str
    name_change_blocked: bool
    entered_events: List[int]
    kit: Optional[str] = None
    last_deadline_bank: int
    last_deadline_value: int
    last_deadline_total_transfers: int
    club_badge_src: Optional[str] = None
    
    class Config:
        extra = "allow"

# Models for league standings endpoint

class LeagueStandingEntry(BaseModel):
    """Individual entry in league standings"""
    id: int
    event_total: int
    player_name: str
    rank: int
    last_rank: int
    rank_sort: int
    total: int
    entry: int
    entry_name: str
    
    class Config:
        extra = "allow"

class LeagueStandings(BaseModel):
    """League standings response"""
    has_next: bool
    page: int
    results: List[LeagueStandingEntry]
    
    class Config:
        extra = "allow"

class LeagueStandingsResponse(BaseModel):
    """Complete league standings response with league info"""
    league: ClassicLeague
    standings: LeagueStandings
    
    class Config:
        extra = "allow"

# Models for manager gameweek picks endpoint

class AutomaticSub(BaseModel):
    """Automatic substitution made during a gameweek"""
    entry: int
    element_in: int
    element_out: int
    event: int

class PickElement(BaseModel):
    """Individual player pick in a gameweek team"""
    element: int
    position: int
    multiplier: int
    is_captain: bool
    is_vice_captain: bool
    
    class Config:
        extra = "allow"

# Models for /me endpoint (current user info)

class UserPlayer(BaseModel):
    """Current user's player information from /me endpoint"""
    first_name: str
    last_name: str
    email: str
    entry: int  # This is the user's team ID
    region: int
    id: int  # Player ID (not team ID)
    
    class Config:
        extra = "allow"

class MeResponse(BaseModel):
    """Response from /me endpoint"""
    player: UserPlayer
    watched: List[Any]

class EntryHistory(BaseModel):
    """Manager's performance for a specific gameweek"""
    event: int
    points: int
    total_points: int
    rank: Optional[int] = None
    rank_sort: Optional[int] = None
    overall_rank: int
    bank: int
    value: int
    event_transfers: int
    event_transfers_cost: int
    points_on_bench: int
    
    class Config:
        extra = "allow"

class GameweekPicks(BaseModel):
    """Manager's team picks for a specific gameweek"""
    active_chip: Optional[str] = None
    automatic_subs: List[AutomaticSub]
    entry_history: EntryHistory
    picks: List[PickElement]
    
    class Config:
        extra = "allow"