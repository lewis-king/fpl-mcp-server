"""
Caching utility with TTL (Time-To-Live) support for FPL data.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

def get_project_root() -> Path:
    """Get the project root directory (where this file's parent's parent is)"""
    return Path(__file__).parent.parent.parent

class CacheMetadata(BaseModel):
    """Metadata for cached data"""
    last_updated: str  # ISO format timestamp
    ttl_hours: int
    
    def is_expired(self) -> bool:
        """Check if the cache has expired based on TTL"""
        last_update = datetime.fromisoformat(self.last_updated)
        expiry_time = last_update + timedelta(hours=self.ttl_hours)
        return datetime.now() > expiry_time
    
    def time_until_expiry(self) -> timedelta:
        """Get time remaining until cache expires"""
        last_update = datetime.fromisoformat(self.last_updated)
        expiry_time = last_update + timedelta(hours=self.ttl_hours)
        return expiry_time - datetime.now()


class DataCache:
    """
    Manages cached data with TTL support.
    Stores data in JSON files with metadata about cache freshness.
    """
    
    def __init__(self, cache_dir: str = "data", ttl_hours: int = 4):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files (relative to project root)
            ttl_hours: Time-to-live in hours (default: 4)
        """
        # Use absolute path relative to project root
        project_root = get_project_root()
        self.cache_dir = project_root / cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.metadata_suffix = ".meta.json"
    
    def _get_metadata_path(self, cache_file: str) -> Path:
        """Get the metadata file path for a cache file"""
        return self.cache_dir / f"{cache_file}{self.metadata_suffix}"
    
    def _get_data_path(self, cache_file: str) -> Path:
        """Get the data file path"""
        return self.cache_dir / cache_file
    
    def _read_metadata(self, cache_file: str) -> Optional[CacheMetadata]:
        """Read cache metadata"""
        metadata_path = self._get_metadata_path(cache_file)
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
                return CacheMetadata(**data)
        except Exception:
            return None
    
    def _write_metadata(self, cache_file: str) -> None:
        """Write cache metadata"""
        metadata = CacheMetadata(
            last_updated=datetime.now().isoformat(),
            ttl_hours=self.ttl_hours
        )
        metadata_path = self._get_metadata_path(cache_file)
        with open(metadata_path, 'w') as f:
            json.dump(metadata.model_dump(), f, indent=2)
    
    def is_expired(self, cache_file: str) -> bool:
        """
        Check if cached data has expired.
        
        Args:
            cache_file: Name of the cache file
            
        Returns:
            True if cache is expired or doesn't exist, False otherwise
        """
        data_path = self._get_data_path(cache_file)
        if not data_path.exists():
            return True
        
        metadata = self._read_metadata(cache_file)
        if metadata is None:
            return True
        
        return metadata.is_expired()
    
    def get(self, cache_file: str, ignore_expiry: bool = False) -> Optional[Any]:
        """
        Get cached data if it exists.
        
        Args:
            cache_file: Name of the cache file
            ignore_expiry: If True, return data even if expired
            
        Returns:
            Cached data or None if missing
        """
        if not ignore_expiry and self.is_expired(cache_file):
            return None
        
        data_path = self._get_data_path(cache_file)
        if not data_path.exists():
            return None
            
        try:
            with open(data_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def set(self, cache_file: str, data: Any) -> None:
        """
        Store data in cache with current timestamp.
        
        Args:
            cache_file: Name of the cache file
            data: Data to cache (must be JSON serializable)
        """
        data_path = self._get_data_path(cache_file)
        
        # Write data
        with open(data_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Write metadata
        self._write_metadata(cache_file)
    
    def invalidate(self, cache_file: str) -> None:
        """
        Invalidate (delete) cached data and metadata.
        
        Args:
            cache_file: Name of the cache file
        """
        data_path = self._get_data_path(cache_file)
        metadata_path = self._get_metadata_path(cache_file)
        
        if data_path.exists():
            data_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()
    
    def get_cache_info(self, cache_file: str) -> Optional[Dict[str, Any]]:
        """
        Get information about cached data.
        
        Args:
            cache_file: Name of the cache file
            
        Returns:
            Dictionary with cache info or None if cache doesn't exist
        """
        metadata = self._read_metadata(cache_file)
        if metadata is None:
            return None
        
        data_path = self._get_data_path(cache_file)
        if not data_path.exists():
            return None
        
        file_size = data_path.stat().st_size
        time_remaining = metadata.time_until_expiry()
        
        return {
            "last_updated": metadata.last_updated,
            "ttl_hours": metadata.ttl_hours,
            "is_expired": metadata.is_expired(),
            "time_remaining_seconds": max(0, int(time_remaining.total_seconds())),
            "file_size_bytes": file_size
        }