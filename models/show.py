"""
Show model for Sync2NAS, representing TV show metadata and database serialization logic.
"""
import os
import datetime
import json
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)

class Show(BaseModel):
    """
    Represents a TV show with metadata from TMDB and local system.

    Attributes:
        sys_name (str): System name for the show (used for directory).
        sys_path (str): Full system path to the show directory.
        tmdb_name (str): Official TMDB name.
        tmdb_aliases (Optional[str]): Alternative names for the show.
        tmdb_id (int): TMDB ID of the show.
        tmdb_first_aired (Optional[datetime.datetime]): First air date.
        tmdb_last_aired (Optional[datetime.datetime]): Last air date.
        tmdb_year (Optional[int]): Year of first air date.
        tmdb_overview (Optional[str]): Show overview.
        tmdb_season_count (Optional[int]): Number of seasons.
        tmdb_episode_count (Optional[int]): Number of episodes.
        tmdb_episode_groups (Optional[str]): Episode group metadata.
        tmdb_status (Optional[str]): TMDB status string.
        tmdb_external_ids (Optional[str]): External IDs (JSON-encoded).
        tmdb_episodes_fetched_at (Optional[datetime.datetime]): Last episode fetch timestamp.
        fetched_at (Optional[datetime.datetime]): Record creation timestamp.

    Methods:
        to_db_tuple(): Serialize for DB insertion.
        from_tmdb(): Construct from TMDB API response.
        from_db_record(): Construct from DB record.
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # System fields
    sys_name: str = Field(..., description="System name for the show (used for directory)")
    sys_path: str = Field(..., description="Full system path to the show directory")
    
    # TMDB fields
    tmdb_name: str = Field(..., description="Official TMDB name")
    tmdb_aliases: Optional[str] = Field(None, description="Alternative names for the show")
    tmdb_id: int = Field(..., ge=0, description="TMDB ID of the show")
    tmdb_first_aired: Optional[datetime.datetime] = Field(None, description="First air date")
    tmdb_last_aired: Optional[datetime.datetime] = Field(None, description="Last air date")
    tmdb_year: Optional[int] = Field(None, ge=1900, le=2100, description="Year of first air date")
    tmdb_overview: Optional[str] = Field(None, description="Show overview")
    tmdb_season_count: Optional[int] = Field(None, ge=0, description="Number of seasons")
    tmdb_episode_count: Optional[int] = Field(None, ge=0, description="Number of episodes")
    tmdb_episode_groups: Optional[str] = Field(None, description="Episode group metadata (JSON)")
    tmdb_status: Optional[str] = Field(None, description="TMDB status string")
    tmdb_external_ids: Optional[str] = Field(None, description="External IDs (JSON-encoded)")
    tmdb_episodes_fetched_at: Optional[datetime.datetime] = Field(None, description="Last episode fetch timestamp")
    fetched_at: datetime.datetime = Field(default_factory=datetime.datetime.now, description="Record creation timestamp")

    def to_db_tuple(self) -> tuple:
        """
        Serialize the Show object as a tuple for database insertion.

        Returns:
            tuple: Values for DB insertion.
        """
        return (
            self.sys_name,
            self.sys_path,
            self.tmdb_name,
            self.tmdb_aliases,
            self.tmdb_id,
            self.tmdb_first_aired,
            self.tmdb_last_aired,
            self.tmdb_year,
            self.tmdb_overview,
            self.tmdb_season_count,
            self.tmdb_episode_count,
            self.tmdb_episode_groups,
            self.tmdb_episodes_fetched_at,
            self.tmdb_status,
            self.tmdb_external_ids,
            self.fetched_at
        )

    @classmethod
    def from_tmdb(cls, show_details: dict, sys_name: Optional[str] = None, sys_path: Optional[str] = None) -> "Show":
        """
        Construct a Show object from TMDB API response.

        Args:
            show_details (dict): TMDB API response for the show.
            sys_name (Optional[str]): System name override.
            sys_path (Optional[str]): System path override.

        Returns:
            Show: Instantiated Show object.
        """
        # Create the individual dicts for each section of the show_details
        info = show_details["info"]
        episode_groups = show_details["episode_groups"]
        external_ids = show_details["external_ids"]
        original_name = info.get("original_name")
        name = info.get("name")
        alternative_titles = show_details["alternative_titles"]
        first_air = info.get("first_air_date")
        last_air = info.get("last_air_date")
        year = int(first_air[:4]) if first_air else None
        show_id = info.get("id")
        overview = info.get("overview")
        status = info.get("status")
        season_count = info.get("number_of_seasons")
        episode_count = info.get("number_of_episodes")
        
        show_external_ids = json.dumps(external_ids)
        if isinstance(episode_groups, dict) and "results" in episode_groups:
            show_episode_groups = json.dumps(episode_groups["results"])
        else:
            show_episode_groups = "[]"

        logger.debug(f"Alternative titles: {alternative_titles}, name: {name}, sys_name: {sys_name}, original_name: {original_name}")
        # Filter out None values before extending
        additional_titles = []
        if original_name:
            additional_titles.append({'title': original_name})
        if name:
            additional_titles.append({'title': name})
        if sys_name:
            additional_titles.append({'title': sys_name})
        alternative_titles['results'].extend(additional_titles)
        logger.debug(f"Alternative titles after extend: {alternative_titles}")
        aliases = sorted(set(x['title'] for x in alternative_titles.get('results', []) if x.get('title')))
        aliases = ",".join(aliases)

        return cls(
            sys_name=sys_name,
            sys_path=sys_path,
            tmdb_name=name,
            tmdb_aliases=aliases,
            tmdb_id=show_id,
            tmdb_first_aired=datetime.datetime.fromisoformat(first_air) if first_air else None,
            tmdb_last_aired=datetime.datetime.fromisoformat(last_air) if last_air else None,
            tmdb_year=year,
            tmdb_overview=overview,
            tmdb_season_count=season_count,
            tmdb_episode_count=episode_count,
            tmdb_episode_groups=show_episode_groups,
            tmdb_status=status,
            tmdb_external_ids=show_external_ids,
            tmdb_episodes_fetched_at=None
        )

    @classmethod
    def from_db_record(cls, record: dict) -> "Show":
        """
        Construct a Show object from a database record.

        Args:
            record (dict): Database record for the show.

        Returns:
            Show: Instantiated Show object.
        """
        # Handle None fetched_at by using default factory
        fetched_at = record["fetched_at"] if record["fetched_at"] is not None else datetime.datetime.now()
        
        return cls(
            sys_name=record["sys_name"],
            sys_path=record["sys_path"],
            tmdb_id=record["tmdb_id"],
            tmdb_name=record["tmdb_name"],
            tmdb_aliases=record["tmdb_aliases"],
            tmdb_first_aired=record["tmdb_first_aired"],
            tmdb_last_aired=record["tmdb_last_aired"],
            tmdb_year=record["tmdb_year"],
            tmdb_overview=record["tmdb_overview"],
            tmdb_season_count=record["tmdb_season_count"],
            tmdb_episode_count=record["tmdb_episode_count"],
            tmdb_episode_groups=record["tmdb_episode_groups"],
            tmdb_status=record["tmdb_status"],
            tmdb_external_ids=record["tmdb_external_ids"],
            tmdb_episodes_fetched_at=record["tmdb_episodes_fetched_at"],
            fetched_at=fetched_at
        )

    def get_episode_groups_dict(self) -> Optional[Dict[str, Any]]:
        """
        Get episode groups as a dictionary.
        
        Returns:
            Optional[Dict[str, Any]]: Parsed episode groups or None.
        """
        if not self.tmdb_episode_groups:
            return None
        try:
            parsed = json.loads(self.tmdb_episode_groups)
            # Return None for empty arrays to maintain consistent behavior
            return parsed if parsed else None
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse episode groups JSON for show {self.tmdb_id}")
            return None

    def get_external_ids_dict(self) -> Optional[Dict[str, Any]]:
        """
        Get external IDs as a dictionary.
        
        Returns:
            Optional[Dict[str, Any]]: Parsed external IDs or None.
        """
        if not self.tmdb_external_ids:
            return None
        try:
            return json.loads(self.tmdb_external_ids)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse external IDs JSON for show {self.tmdb_id}")
            return None