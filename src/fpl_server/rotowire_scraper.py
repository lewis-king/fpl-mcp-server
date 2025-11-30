"""
RotoWire scraper for Premier League lineup predictions and injury status.
"""
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlayerLineupStatus:
    """Player lineup status from RotoWire"""
    player_name: str
    team: str
    status: str  # OUT, DOUBTFUL, EXPECTED, CONFIRMED
    reason: str
    confidence: float

class RotoWireLineupScraper:
    """Dedicated scraper for RotoWire Premier League lineup predictions"""
    
    def __init__(self):
        self.base_url = "https://www.rotowire.com/soccer/lineups.php"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def scrape_premier_league_lineups(self) -> List[PlayerLineupStatus]:
        """
        Scrape RotoWire Premier League lineup predictions to get comprehensive player status data.
        
        Returns a list of PlayerLineupStatus objects with OUT, DOUBTFUL, EXPECTED, CONFIRMED players.
        """
        logger.info("🔍 Scraping RotoWire Premier League lineups...")
        
        try:
            url = self.base_url
            
            logger.info(f"Fetching RotoWire lineups from: {url}")
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch RotoWire page: HTTP {response.status_code}")
                    return []
                
                logger.info(f"Successfully fetched page (Status: {response.status_code})")
                
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract lineup data using the actual HTML structure
            lineup_statuses = self._parse_lineup_data(soup)
            
            logger.info(f"✅ Successfully scraped {len(lineup_statuses)} player statuses from RotoWire")
            
            # Log summary
            status_counts = {}
            for status in lineup_statuses:
                status_counts[status.status] = status_counts.get(status.status, 0) + 1
            
            for status_type, count in status_counts.items():
                logger.info(f"  📊 {status_type}: {count} players")
            
            return lineup_statuses
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape RotoWire lineups: {e}")
            return []
    
    def _parse_lineup_data(self, soup: BeautifulSoup) -> List[PlayerLineupStatus]:
        """
        Parse the RotoWire lineup page to extract player status information.
        
        Look directly for li.lineup__player elements with injury information.
        """
        lineup_statuses = []
        
        try:
            # Look directly for all player entries with injury status
            player_entries = soup.find_all('li', class_='lineup__player')
            logger.info(f"Found {len(player_entries)} total player entries")
            
            # Also look for injury spans to find injured players
            injury_spans = soup.find_all('span', class_='lineup__inj')
            logger.info(f"Found {len(injury_spans)} injury status indicators")
            
            # Process each player entry
            for player_entry in player_entries:
                try:
                    # Extract player name
                    name_link = player_entry.find('a')
                    if not name_link:
                        continue
                    
                    # Get full name from title attribute, fallback to text
                    player_name = name_link.get('title', '').strip()
                    if not player_name:
                        player_name = name_link.get_text(strip=True)
                    
                    if not player_name:
                        continue
                    
                    # Extract position
                    pos_element = player_entry.find('div', class_='lineup__pos')
                    position = pos_element.get_text(strip=True) if pos_element else 'Unknown'
                    
                    # Try to determine team by looking at parent structure
                    team = 'Unknown'
                    parent_ul = player_entry.find_parent('ul', class_='lineup__list')
                    if parent_ul:
                        # Look for team abbreviation in the same section
                        lineup_section = parent_ul.find_parent('div')
                        if lineup_section:
                            team_abbrs = lineup_section.find_all('div', class_='lineup__abbr')
                            if team_abbrs:
                                # Determine if this is home or away team based on list position
                                all_lists = lineup_section.find_all('ul', class_='lineup__list')
                                if len(all_lists) >= 2 and len(team_abbrs) >= 2:
                                    list_index = all_lists.index(parent_ul)
                                    team = team_abbrs[list_index].get_text(strip=True) if list_index < len(team_abbrs) else team_abbrs[0].get_text(strip=True)
                    
                    # Extract injury status
                    injury_element = player_entry.find('span', class_='lineup__inj')
                    
                    if injury_element:
                        injury_status = injury_element.get_text(strip=True)
                        
                        # Map RotoWire status to our format
                        if injury_status == 'OUT':
                            status = 'OUT'
                            reason = 'Listed as OUT on RotoWire'
                            confidence = 0.95
                        elif injury_status in ['QUES', 'DOUBTFUL']:
                            status = 'DOUBTFUL'
                            reason = 'Listed as QUESTIONABLE on RotoWire'
                            confidence = 0.75
                        elif injury_status == 'SUS':
                            status = 'OUT'
                            reason = 'Suspended'
                            confidence = 1.0
                        else:
                            status = 'DOUBTFUL'
                            reason = f'Listed as {injury_status} on RotoWire'
                            confidence = 0.6
                        
                        player_status = PlayerLineupStatus(
                            player_name=player_name,
                            team=team,
                            status=status,
                            reason=reason,
                            confidence=confidence
                        )
                        
                        lineup_statuses.append(player_status)
                        logger.info(f"Found injured/suspended player: {player_name} ({team}) - {status}")
                
                except Exception as e:
                    logger.warning(f"Error parsing player entry: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(lineup_statuses)} player statuses from RotoWire")
            return lineup_statuses
            
        except Exception as e:
            logger.error(f"Error parsing RotoWire lineup data: {e}")
            return []
    
    def convert_to_ai_format(self, lineup_statuses: List[PlayerLineupStatus]) -> Dict[str, Any]:
        """
        Convert RotoWire lineup statuses to the AI recommendations format.
        
        This ensures compatibility with the existing pipeline.
        """
        players_to_avoid = []
        lineup_predictions = []
        
        for status in lineup_statuses:
            # Add to lineup predictions
            lineup_predictions.append({
                "player_name": status.player_name,
                "team": status.team,
                "status": status.status,
                "reason": status.reason,
                "confidence": status.confidence
            })
            
            # Add OUT and DOUBTFUL players to avoid list
            if status.status in ["OUT", "DOUBTFUL"]:
                risk_level = "high" if status.status == "OUT" else "medium"
                predicted_points = 0.0 if status.status == "OUT" else 2.0
                
                players_to_avoid.append({
                    "player_name": status.player_name,
                    "reason": f"{status.status} - {status.reason}",
                    "predicted_points_next_3_gameweeks": predicted_points,
                    "risk_level": risk_level
                })
        
        return {
            "players_to_avoid": players_to_avoid,
            "lineup_predictions": lineup_predictions
        }