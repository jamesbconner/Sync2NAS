import os
import datetime
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Show:
    def __init__(self,
                 sys_name: str,
                 sys_path: str,
                 tmdb_name: str,
                 tmdb_aliases: Optional[str],
                 tmdb_id: int,
                 tmdb_first_aired: Optional[datetime.datetime],
                 tmdb_last_aired: Optional[datetime.datetime],
                 tmdb_year: Optional[int],
                 tmdb_overview: Optional[str],
                 tmdb_season_count: Optional[int],
                 tmdb_episode_count: Optional[int],
                 tmdb_episode_groups: Optional[str],
                 tmdb_status: Optional[str] = None,
                 tmdb_external_ids: Optional[str] = None,
                 tmdb_episodes_fetched_at: Optional[datetime.datetime] = None,
                 fetched_at: Optional[datetime.datetime] = None):

        self.sys_name = sys_name
        self.sys_path = sys_path
        self.tmdb_name = tmdb_name
        self.tmdb_aliases = tmdb_aliases
        self.tmdb_id = tmdb_id
        self.tmdb_first_aired = tmdb_first_aired
        self.tmdb_last_aired = tmdb_last_aired
        self.tmdb_year = tmdb_year
        self.tmdb_overview = tmdb_overview
        self.tmdb_season_count = tmdb_season_count
        self.tmdb_episode_count = tmdb_episode_count
        self.tmdb_episode_groups = tmdb_episode_groups
        self.tmdb_episodes_fetched_at = tmdb_episodes_fetched_at
        self.tmdb_status = tmdb_status
        self.tmdb_external_ids = tmdb_external_ids
        self.fetched_at = datetime.datetime.now()

    def to_db_tuple(self):
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
            json.dumps(self.tmdb_episode_groups) if isinstance(self.tmdb_episode_groups, list) else self.tmdb_episode_groups,
            self.tmdb_episodes_fetched_at,
            self.tmdb_status,
            json.dumps(self.tmdb_external_ids) if isinstance(self.tmdb_external_ids, dict) else self.tmdb_external_ids,
            self.fetched_at
        )

    @classmethod
    def from_tmdb(cls, show_details: dict, sys_name: Optional[str] = None, sys_path: Optional[str] = None):
        # Create the individual dicts for each section of the show_details
        info = show_details["info"]
        episode_groups = show_details["episode_groups"]
        external_ids = show_details["external_ids"]
        original_name = info.get("original_name")
        name = info.get("name")
        alternative_titles = show_details["alternative_titles"]
        alternative_titles = alternative_titles.append(original_name).append(name).append(sys_name)
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
            show_episode_groups = []

        aliases = sorted(set(x['title'] for x in alternative_titles.get('results', [])))
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
            tmdb_episodes_fetched_at=None,
            fetched_at=datetime.datetime.now()
        )

    @classmethod
    def from_db_record(cls, record: dict) -> "Show":
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
            fetched_at=record["fetched_at"]
        )