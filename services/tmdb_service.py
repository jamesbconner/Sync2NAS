import tmdbsimple as tmdb
import logging
import requests

logger = logging.getLogger(__name__)

class TMDBService:
    """
    Service for interacting with the TMDB API to search for shows and movies, and retrieve detailed metadata.

    Methods:
        search_show(name): Search for a show by name.
        search_movie(name): Search for a movie by name.
        get_show_details(id): Get detailed metadata for a show.
        get_show_season_details(id, season): Get details for a specific season of a show.
        get_show_episode_details(id, season, episode): Get details for a specific episode of a show.
        get_episode_group_details(id): Get details for a specific episode group.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        tmdb.API_KEY = self.api_key

    def search_show(self, name: str) -> dict:
        """ Search for a show by name
        
        Args:
            name: The name of the show to search for
        
        Returns:
            A dictionary containing the search results with the following keys:
            - page: The page number of the search results
            - results: A list of dicts containing the search results
                - adult: Whether the show is an adult show
                - backdrop_path: The backdrop path of the show
                - genre_ids: A list of genre IDs
                - id: The ID of the show
                - original_country: The original country of the show
                - original_language: The original language of the show
                - original_name: The original name of the show
                - overview: The overview of the show
                - popularity: The popularity of the show
                - poster_path: The poster path of the show
                - first_air_date: The first air date of the show
                - name: The name of the show
                - vote_average: The vote average of the show
                - vote_count: The vote count of the show
            - total_pages: The total number of pages of search results
            - total_results: The total number of search results
            None if an error occurs.
        """
        try:
            search = tmdb.Search()
            response = search.tv(query=name, include_adult=True)
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error searching for show {name}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None

    def search_movie(self, name: str) -> dict:
        """ Search for a movie by name
        
        Args:
            name: The name of the movie to search for
        
        Returns:
            A dictionary containing the search results with the following keys:
            - page: The page number of the search results
            - results: A list of dicts containing the search results
                - adult: Whether the movie is an adult movie
                - backdrop_path: The backdrop path of the movie
                - genre_ids: A list of genre IDs
                - id: The ID of the movie
                - original_language: The original language of the movie
                - original_title: The original title of the movie
                - overview: The overview of the movie
                - popularity: The popularity of the movie
                - poster_path: The poster path of the movie
                - release_date: The release date of the movie
                - title: The title of the movie
                - vote_average: The vote average of the movie
                - vote_count: The vote count of the movie
            - total_pages: The total number of pages of search results
            - total_results: The total number of search results
            None if an error occurs.
        """
        try:
            search = tmdb.Search()
            response = search.movie(query=name, include_adult=True)
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error searching for movie {name}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None

    def get_show_details(self, id: int) -> dict:
        """ Get the details of a specific show
        
        Args:
            id: The ID of the show
        
        Returns:
            A dictionary containing the details of the show with the following keys:
            - info: An info dictionary
            - episode_groups: An episode_groups dictionary
            - alternative_titles: An alternative_titles dictionary
            - external_ids: An external_ids dictionary

            Details on each dictionary:
           info:
            - adult: Whether the show is an adult show
            - backdrop_path: The backdrop path of the show
            - created_by: A list of dicts containing the created by details
                - id: The ID of the created by
                - name: The name of the created by
                - gender: The gender of the created by
                - profile_path: The profile path of the created by
            - episode_run_time: The episode run time of the show
            - first_air_date: The first air date of the show
            - genres: A list of dicts containing the genres of the show
                - id: The ID of the genre
                - name: The name of the genre
            - homepage: The homepage of the show
            - id: The ID of the show
            - in_production: Whether the show is in production
            - languages: A list of languages of the show
                - english_name: The english name of the language
                - iso_639_1: The ISO 639-1 code of the language
                - name: The name of the language
            - last_air_date: The last air date of the show
            - last_episode_to_air: The last episode to air of the show
            - name: The name of the show
            - next_episode_to_air: The next episode to air of the show
            - networks: A list of dicts containing the networks of the show
                - id: The ID of the network
                - name: The name of the network
                - logo_path: The logo path of the network
                - origin_country: The origin country of the network
            - number_of_episodes: The number of episodes of the show
            - number_of_seasons: The number of seasons of the show
            - origin_country: The origin country of the show
            - original_language: The original language of the show
            - original_name: The original name of the show
            - overview: The overview of the show
            - popularity: The popularity of the show
            - poster_path: The poster path of the show
            - production_companies: A list of dicts containing the production companies of the show
                - id: The ID of the production company  
                - logo_path: The logo path of the production company
                - name: The name of the production company
                - origin_country: The origin country of the production company
            - seasons: A list of dicts containing the seasons of the show
                - air_date: The air date of the season
                - episode_count: The episode count of the season
                - id: The ID of the season
                - name: The name of the season
                - overview: The overview of the season
                - poster_path: The poster path of the season
                - season_number: The season number
                - vote_average: The vote average of the season
                - vote_count: The vote count of the season
            - spoken_languages: A list of dicts containing the spoken languages of the show
                - english_name: The english name of the language
                - iso_639_1: The ISO 639-1 code of the language
                - name: The name of the language
            - status: The status of the show
            - tagline: The tagline of the show
            - type: The type of the show
            - vote_average: The vote average of the show
            - vote_count: The vote count of the show
            
            episode_groups:
            - results: A list of dicts containing the episode groups of the show
                - description: The description of the episode group
                - episode_count: The episode count of the episode group
                - group_count: The group count of the episode group
                - id: The ID of the episode group
                - name: The name of the episode group
                - type: The type of the episode group
            - id: The ID of the show
                
            alternative_titles:
            - id: The ID of the show
            - results: A list of dicts containing the alternative titles of the show
                - iso_3166_1: The ISO 3166-1 code of the country
                - title: The title of the alternative title
                - type: The type of the alternative title
            
            external_ids:
            - id: The ID of the show
            - imdb_id: The IMDB ID of the show
            - freebase_mid: The Freebase MID of the show
            - freebase_id: The Freebase ID of the show
            - tvdb_id: The TVDB ID of the show
            - tvrage_id: The TVRage ID of the show
            - wikidata_id: The Wikidata ID of the show
            - facebook_id: The Facebook ID of the show
            - instagram_id: The Instagram ID of the show
            - twitter_id: The Twitter ID of the show
            
            None if an error occurs.
        """
        try:
            show = tmdb.TV(id=id)
            return {"info": show.info(), "episode_groups": show.episode_groups(), "alternative_titles": show.alternative_titles(), "external_ids": show.external_ids()}
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting show details for show {id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None
    
    def get_show_season_details(self, id: int, season: int) -> dict:
        """ Get the details of a specific season for a show
        
        Args:
            id: The ID of the show
            season: The season number

        Returns:
            A dictionary containing the details of the season with the following keys:
            - id: The ID of the season
            - air_date: The air date of the season
            - episodes: A list of dicts containing episode details
                - air_date: The air date of the episode
                - episode_number: The episode number
                - episode_type: The type of episode
                - id: The ID of the episode
                - name: The name of the episode
                - overview: The overview of the episode
                - production_code: The production code of the episode
                - season_number: The season number
                - show_id: The ID of the show
                - still_path: The still path of the episode
                - vote_average: The vote average of the episode
                - vote_count: The vote count of the episode
                - crew: A list of dicts containing crew details
            None if an error occurs.
        """
        try:
            results = tmdb.TV_Seasons(tv_id=id, season_number=season)
            return results.info()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting season details for show {id} season {season}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None
    
    def get_show_episode_details(self, id: int, season: int, episode: int) -> dict:
        """ Get the details of a specific episode for a show
        
        Note: Anime shows are often compacted into a single season or split into multiple named shows.
        If getting 404 errors, use season 1 and the absolute episode number, or search for the season's named show.
        Season 0 is the standard season for special TV episodes and OVA's.
        
        Args:
            id: The ID of the show
            season: The season number
            episode: The episode number
        
        Returns:
            A dictionary containing the details of the episode with the following keys:
            - air_date: The air date of the episode
            - crew: A list of dicts containing crew details
                - id: The ID of the crew member
                - name: The name of the crew member
                - gender: The gender of the crew member
                - profile_path: The profile path of the crew member
            - episode_number: The episode number
            - guest_stars: A list of dicts containing guest star details
                - id: The ID of the guest star
                - name: The name of the guest star
                - character: The character of the guest star
            - id: The ID of the episode
            - name: The name of the episode
            - overview: The overview of the episode
            - production_code: The production code of the episode
            - season_number: The season number
            - show_id: The ID of the show
            - still_path: The still path of the episode
            - vote_average: The vote average of the episode
            - vote_count: The vote count of the episode
            None if an error occurs.
        """
        try: 
            results = tmdb.TV_Episodes(tv_id=id, season_number=season, episode_number=episode)
            return results.info()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting episode details for show {id} season {season} episode {episode}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None

    def get_episode_group_details(self, id: str) -> dict:
        """ Get the details of a specific episode group
        
        Notes on Episode Groups:
            1. Episode Group IDs are fetched via the get_show_details function. The episode_groups key contains a list of episode groups.
            2. There are 7 types of episode groups, enumerated below.
        
        Episode Group Types:
            1. Original air date
            2. Absolute
            3. DVD
            4. Digital
            5. Story arc
            6. Production (typically our preferred type, as it contains the seasonality and absolute episode numbers)
            7. TV
        
        Args:
            id: The alphanumeric ID of the episode group, not the show ID.
        
        Returns:
            A dictionary containing the details of the episode group with the following keys:
            - id: The ID of the episode group
            - name: The name of the episode group
            - type: The type of the episode group
            - network: The network of the episode group
            - description: The description of the episode group
            - episode_count: The episode count of the episode group
            - group_count: The group count of the episode group
            - groups: A list of dicts containing the groups (seasons for type 6) of the episode group
                - id: The ID of the episode group
                - name: The name of the episode group (typically the season name)
                - order: The order of the episode group
                - locked: Whether the episode group is locked (true if it is, false if it is not)
                - episodes: A list of dicts containing the episodes of the episode group
                    - air_date: The air date of the episode
                    - episode_number: The episode number (absolute episode number)
                    - episode_type: The type of episode (standard, special, finale, etc.)
                    - id: The ID of the episode
                    - name: The name of the episode
                    - overview: The overview of the episode
                    - production_code: The production code of the episode
                    - runtime: The runtime of the episode
                    - season_number: The season number (not trustworthy, given compression of seasons for anime)
                    - show_id: The ID of the show
                    - still_path: The still path of the episode
                    - vote_average: The vote average of the episode
                    - vote_count: The vote count of the episode
                    - order: The order of the episode (seasonal episode number)

            
            None if an error occurs.
        """
        try:
            grp = tmdb.TV_Episode_Groups(id=id)
            return grp.info()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting episode group details for show {id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None
