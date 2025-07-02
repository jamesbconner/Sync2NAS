import pytest
import tempfile
import os
from services.db_implementations.sqlite_implementation import SQLiteDBService

class DummyShow:
    def __init__(self, sys_name, sys_path, tmdb_name):
        self.sys_name = sys_name
        self.sys_path = sys_path
        self.tmdb_name = tmdb_name
    def to_db_tuple(self):
        # Fill with enough fields for the insert
        return (
            self.sys_name, self.sys_path, self.tmdb_name, '', 1, None, None, None, '', 1, 1, '', None, '', '', None
        )

class DummyEpisode:
    def __init__(self, tmdb_id, season, episode, name):
        self.tmdb_id = tmdb_id
        self.season = season
        self.episode = episode
        self.abs_episode = 1
        self.episode_type = ''
        self.episode_id = 1
        self.air_date = None
        self.fetched_at = None
        self.name = name
        self.overview = ''
    def to_db_tuple(self):
        return (
            self.tmdb_id, self.season, self.episode, self.abs_episode, self.episode_type, self.episode_id, self.air_date, self.fetched_at, self.name, self.overview
        )

@pytest.fixture
def temp_db_file():
    """Fixture providing a temporary SQLite database file."""
    fd, path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_initialize_creates_schema(temp_db_file):
    """Test that initialize creates the database schema without error."""
    db = SQLiteDBService(temp_db_file)
    db.initialize()
    # Check that the file exists and is not empty
    assert os.path.exists(temp_db_file)
    assert os.path.getsize(temp_db_file) > 0

def test_add_and_get_show(temp_db_file):
    """Test that a show can be added and retrieved by sys_name."""
    db = SQLiteDBService(temp_db_file)
    db.initialize()
    show = DummyShow('TestShow', '/shows/TestShow', 'Test Show')
    db.add_show(show)
    result = db.get_show_by_sys_name('TestShow')
    assert result is not None
    assert result['sys_name'] == 'TestShow'
    assert result['tmdb_name'] == 'Test Show'

def test_show_exists(temp_db_file):
    """Test that show_exists returns True for an added show and False otherwise."""
    db = SQLiteDBService(temp_db_file)
    db.initialize()
    show = DummyShow('TestShow', '/shows/TestShow', 'Test Show')
    db.add_show(show)
    assert db.show_exists('TestShow')
    assert not db.show_exists('NonexistentShow')

def test_add_and_get_episode(temp_db_file):
    """Test that an episode can be added and retrieved by tmdb_id."""
    db = SQLiteDBService(temp_db_file)
    db.initialize()
    show = DummyShow('TestShow', '/shows/TestShow', 'Test Show')
    db.add_show(show)
    episode = DummyEpisode(1, 1, 1, 'Pilot')
    db.add_episode(episode)
    episodes = db.get_episodes_by_tmdb_id(1)
    assert len(episodes) == 1
    assert episodes[0]['name'] == 'Pilot'

def test_backup_database_creates_file(temp_db_file):
    """Test that backup_database creates a backup file and returns its path."""
    db = SQLiteDBService(temp_db_file)
    db.initialize()
    backup_path = db.backup_database()
    assert os.path.exists(backup_path)
    assert backup_path != temp_db_file 