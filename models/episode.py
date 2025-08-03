"""
Episode model for Sync2NAS, representing episode metadata and database serialization logic.
"""
import datetime
import logging
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from services.tmdb_service import TMDBService

logger = logging.getLogger(__name__)

class Episode(BaseModel):
    """
    Represents a TV episode with metadata from TMDB and local system.

    Attributes:
        tmdb_id (int): TMDB ID of the show.
        season (int): Season number.
        episode (int): Episode number.
        abs_episode (int): Absolute episode number.
        episode_type (str): Type of episode (e.g., standard, special).
        episode_id (int): TMDB episode ID.
        air_date (Optional[datetime.datetime]): Air date.
        fetched_at (datetime.datetime): Record creation timestamp.
        name (str): Episode title.
        overview (str): Episode overview.

    Methods:
        to_db_tuple(): Serialize for DB insertion.
        parse_from_tmdb(): Construct episodes from TMDB API response.
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # TMDB fields
    tmdb_id: int = Field(..., gt=0, description="TMDB ID of the show")
    season: int = Field(..., ge=0, description="Season number")
    episode: int = Field(..., ge=0, description="Episode number")
    abs_episode: int = Field(..., ge=1, description="Absolute episode number")
    episode_type: str = Field(..., description="Type of episode (e.g., standard, special)")
    episode_id: int = Field(..., gt=0, description="TMDB episode ID")
    air_date: Optional[datetime.datetime] = Field(None, description="Air date")
    fetched_at: datetime.datetime = Field(default_factory=datetime.datetime.now, description="Record creation timestamp")
    name: str = Field(..., description="Episode title")
    overview: str = Field(..., description="Episode overview")

    def to_db_tuple(self) -> tuple:
        """
        Serialize the Episode object as a tuple for database insertion.

        Returns:
            tuple: Values for DB insertion.
        """
        return (
            self.tmdb_id,
            self.season,
            self.episode,
            self.abs_episode,
            self.episode_type,
            self.episode_id,
            self.air_date,
            self.fetched_at,
            self.name,
            self.overview
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime.datetime]:
        """
        Parse a date string in ISO format to a datetime object.

        Args:
            date_str (Optional[str]): Date string in ISO format.

        Returns:
            Optional[datetime.datetime]: Parsed datetime or None if invalid.
        """
        if not date_str:
            return None
        try:
            return datetime.datetime.fromisoformat(date_str)
        except ValueError:
            return None

    @classmethod
    def parse_from_tmdb(cls, tmdb_id: int, tmdb_service: TMDBService, episode_groups: list, season_count: int) -> List["Episode"]:
        """
        Construct a list of Episode objects from TMDB API response.

        Args:
            tmdb_id (int): TMDB ID of the show.
            tmdb_service (TMDBService): TMDB service instance.
            episode_groups (list): Episode group metadata from TMDB.
            season_count (int): Number of seasons.

        Returns:
            List[Episode]: List of Episode objects.
        """
        try:
            return cls._from_production_groups(tmdb_id, tmdb_service, episode_groups)
        except Exception as e:
            logger.warning(f"Production episode group parsing failed for {tmdb_id}: {e}")
            try:
                return cls._from_seasons(tmdb_id, tmdb_service, season_count)
            except Exception as e:
                logger.warning(f"Season parsing failed for {tmdb_id}: {e}")
                return []

    @classmethod
    def _from_production_groups(cls, tmdb_id: int, tmdb_service: TMDBService, episode_groups_meta: list) -> List["Episode"]:
        """
        Construct episodes from TMDB production episode groups.

        Args:
            tmdb_id (int): TMDB ID of the show.
            tmdb_service (TMDBService): TMDB service instance.
            episode_groups_meta (list): Production episode group metadata.

        Returns:
            List[Episode]: List of Episode objects.
        """
        prod_groups = [grp for grp in episode_groups_meta if grp.get("type") == 6]
        if not prod_groups:
            raise ValueError("No production episode groups found")

        episodes = []
        for group in prod_groups:
            group_details = tmdb_service.get_episode_group_details(group["id"])
            if not group_details or not group_details.get("groups"):
                logger.warning(f"Skipping group {group['id']}: No episode data available")
                continue

            for season in group_details["groups"]:
                season_num = season.get("order")
                for ep in season.get("episodes", []):
                    try:
                        episodes.append(cls(
                            tmdb_id=tmdb_id,
                            season=season_num,
                            episode=ep.get("order", 0) + 1,
                            abs_episode=ep.get("episode_number"),
                            episode_type=ep.get("episode_type", "standard"),
                            episode_id=ep.get("id"),
                            air_date=cls._parse_date(ep.get("air_date")),
                            name=ep.get("name", ""),
                            overview=ep.get("overview", "")
                        ))
                    except Exception as e:
                        logger.warning(f"Skipping episode due to error: {e}")
        return episodes

    @classmethod
    def _from_seasons(cls, tmdb_id: int, tmdb_service: TMDBService, season_count: int) -> List["Episode"]:
        """
        Construct episodes from TMDB season data.

        Args:
            tmdb_id (int): TMDB ID of the show.
            tmdb_service (TMDBService): TMDB service instance.
            season_count (int): Number of seasons.

        Returns:
            List[Episode]: List of Episode objects.
        """
        episodes = []
        abs_ep = 1

        for season_num in range(1, season_count + 1):
            try:
                season_data = tmdb_service.get_show_season_details(tmdb_id, season_num)
                if not season_data or "episodes" not in season_data:
                    continue

                for ep in season_data["episodes"]:
                    # Skip episodes missing required fields
                    if not all(key in ep for key in ["episode_number", "name", "id"]):
                        continue

                    try:
                        episodes.append(cls(
                            tmdb_id=tmdb_id,
                            season=season_num,
                            episode=ep["episode_number"],
                            abs_episode=abs_ep,
                            episode_type=ep.get("episode_type", "standard"),
                            episode_id=ep["id"],
                            air_date=cls._parse_date(ep.get("air_date")),
                            name=ep["name"],
                            overview=ep.get("overview", "")
                        ))
                        abs_ep += 1
                    except Exception as e:
                        logger.warning(f"Skipping episode due to error: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Error processing season {season_num}: {e}")
                continue

        return episodes

    @classmethod
    def from_db_record(cls, record: dict) -> "Episode":
        """
        Construct an Episode object from a database record.

        Args:
            record (dict): Database record for the episode.

        Returns:
            Episode: Instantiated Episode object.
        """
        return cls(
            tmdb_id=record["tmdb_id"],
            season=record["season"],
            episode=record["episode"],
            abs_episode=record["abs_episode"],
            episode_type=record["episode_type"],
            episode_id=record["episode_id"],
            air_date=record["air_date"],
            fetched_at=record["fetched_at"],
            name=record["name"],
            overview=record["overview"]
        )