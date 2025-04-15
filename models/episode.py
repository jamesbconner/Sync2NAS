import datetime
import logging
from typing import Optional, List
from services.tmdb_service import TMDBService

logger = logging.getLogger(__name__)

class Episode:
    def __init__(self,
                 tmdb_id: int,
                 season: int,
                 episode: int,
                 abs_episode: int,
                 episode_type: str,
                 episode_id: int,
                 air_date: Optional[datetime.datetime],
                 fetched_at: datetime.datetime,
                 name: str,
                 overview: str):

        self.tmdb_id = tmdb_id
        self.season = season
        self.episode = episode
        self.abs_episode = abs_episode
        self.episode_type = episode_type
        self.episode_id = episode_id
        self.air_date = air_date
        self.fetched_at = fetched_at
        self.name = name
        self.overview = overview

    def to_db_tuple(self):
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
        if not date_str:
            return None
        try:
            return datetime.datetime.fromisoformat(date_str)
        except ValueError:
            return None

    @classmethod
    def parse_from_tmdb(cls, tmdb_id: int, tmdb_service: TMDBService, episode_groups: list, season_count: int) -> List["Episode"]:
        try:
            return cls._from_production_groups(tmdb_id, tmdb_service, episode_groups)
        except Exception as e:
            logger.warning(f"Production episode group parsing failed for {tmdb_id}: {e}")
            return cls._from_seasons(tmdb_id, tmdb_service, season_count)

    @classmethod
    def _from_production_groups(cls, tmdb_id: int, tmdb_service: TMDBService, episode_groups_meta: list) -> List["Episode"]:
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
                            fetched_at=datetime.datetime.now(),
                            name=ep.get("name", ""),
                            overview=ep.get("overview", "")
                        ))
                    except Exception as e:
                        logger.warning(f"Skipping episode due to error: {e}")
        return episodes

    @classmethod
    def _from_seasons(cls, tmdb_id: int, tmdb_service: TMDBService, season_count: int) -> List["Episode"]:
        episodes = []
        abs_ep = 1

        for season_num in range(1, season_count + 1):
            season_data = tmdb_service.get_show_season_details(tmdb_id, season_num)
            if not season_data or not season_data.get("episodes"):
                logger.warning(f"No data for season {season_num} of show {tmdb_id}")
                continue

            for ep in season_data["episodes"]:
                try:
                    episodes.append(cls(
                        tmdb_id=tmdb_id,
                        season=season_num,
                        episode=ep.get("episode_number"),
                        abs_episode=abs_ep,
                        episode_type=ep.get("episode_type", "standard"),
                        episode_id=ep.get("id"),
                        air_date=cls._parse_date(ep.get("air_date")),
                        fetched_at=datetime.datetime.now(),
                        name=ep.get("name", ""),
                        overview=ep.get("overview", "")
                    ))
                    abs_ep += 1
                except Exception as e:
                    logger.warning(f"Skipping episode in season {season_num} due to error: {e}")

        return episodes