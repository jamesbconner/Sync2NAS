import pytest
from click.testing import CliRunner
from cli.search_show import search_show
from unittest.mock import MagicMock, patch

@pytest.fixture
def runner():
    """Fixture providing a Click CliRunner instance."""
    return CliRunner()

@pytest.fixture
def mock_ctx():
    """Fixture providing a mock Click context with db and tmdb services."""
    db = MagicMock()
    tmdb = MagicMock()
    ctx = MagicMock()
    ctx.obj = {'db': db, 'tmdb': tmdb}
    return ctx, db, tmdb

def test_search_show_lists_all_shows(runner, mock_ctx):
    """Test that running search_show with no arguments lists all shows in the database."""
    ctx, db, tmdb = mock_ctx
    db.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    ]
    result = runner.invoke(search_show, [], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 shows in database" in result.output
    assert "Test Show" in result.output

def test_search_show_exact_match(runner, mock_ctx):
    """Test that search_show finds and displays a show by exact name match."""
    ctx, db, tmdb = mock_ctx
    db.get_show_by_name_or_alias.return_value = {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found exact match for 'Test Show'" in result.output
    assert "Test Show" in result.output

def test_search_show_partial_match(runner, mock_ctx):
    """Test that search_show finds and displays shows by partial name match when no exact match is found."""
    ctx, db, tmdb = mock_ctx
    db.get_show_by_name_or_alias.return_value = None
    db.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    ]
    result = runner.invoke(search_show, ['Test'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 partial match for 'Test'" in result.output or "Found 1 partial matches for 'Test'" in result.output
    assert "Test Show" in result.output

def test_search_show_no_match_offers_tmdb(runner, mock_ctx):
    """Test that search_show offers TMDB search if no matches are found and user declines."""
    ctx, db, tmdb = mock_ctx
    db.get_show_by_name_or_alias.return_value = None
    db.get_all_shows.return_value = []
    with patch('click.confirm', return_value=False):
        result = runner.invoke(search_show, ['NoShow'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "No shows found matching 'NoShow'" in result.output or "No exact match found for 'NoShow'" in result.output
    assert "Would you like to search TMDB for similar shows?" in result.output

def test_search_show_by_tmdb_id_found(runner, mock_ctx):
    """Test that search_show finds and displays a show by TMDB ID."""
    ctx, db, tmdb = mock_ctx
    db.get_show_by_tmdb_id.return_value = {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    result = runner.invoke(search_show, ['--tmdb-id', '123'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found show with TMDB ID 123" in result.output
    assert "Test Show" in result.output

def test_search_show_by_tmdb_id_not_found(runner, mock_ctx):
    """Test that search_show prints error and exits if TMDB ID is not found."""
    ctx, db, tmdb = mock_ctx
    db.get_show_by_tmdb_id.return_value = None
    result = runner.invoke(search_show, ['--tmdb-id', '999'], obj=ctx.obj)
    assert result.exit_code == 1
    assert "No show found with TMDB ID 999" in result.output

def test_search_show_dry_run(runner, mock_ctx):
    """Test that search_show prints dry run info and does not search the database."""
    ctx, db, tmdb = mock_ctx
    result = runner.invoke(search_show, ['--dry-run', 'Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "DRY RUN: Would search for shows" in result.output
    assert "Show name: Test Show" in result.output
    assert not db.get_show_by_name_or_alias.called
    assert not db.get_all_shows.called

def test_search_show_db_error(runner, mock_ctx):
    """Test that search_show prints error and exits if the database call raises an exception."""
    ctx, db, tmdb = mock_ctx
    db.get_all_shows.side_effect = Exception('fail!')
    result = runner.invoke(search_show, [], obj=ctx.obj)
    assert result.exit_code == 1
    assert "Error searching for shows: fail!" in result.output 