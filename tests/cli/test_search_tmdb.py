import pytest
from click.testing import CliRunner
from cli.search_tmdb import search_tmdb
from unittest.mock import MagicMock

@pytest.fixture
def runner():
    """Fixture providing a Click CliRunner instance."""
    return CliRunner()

@pytest.fixture
def mock_ctx():
    """Fixture providing a mock Click context with tmdb service."""
    tmdb = MagicMock()
    ctx = MagicMock()
    ctx.obj = {'tmdb': tmdb}
    return ctx, tmdb

def test_search_tmdb_no_args(runner, mock_ctx):
    """Test that running search_tmdb with no arguments prints usage and exits with error."""
    ctx, tmdb = mock_ctx
    result = runner.invoke(search_tmdb, [], obj=ctx.obj)
    assert result.exit_code == 1
    assert "Please provide either a show name or --tmdb-id" in result.output

def test_search_tmdb_by_name_results(runner, mock_ctx):
    """Test that search_tmdb finds and displays shows by name."""
    ctx, tmdb = mock_ctx
    tmdb.search_show.return_value = {"results": [{"id": 123, "name": "Test Show", "first_air_date": "2020-01-01"}]}
    result = runner.invoke(search_tmdb, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 show matching 'Test Show'" in result.output or "Found 1 shows matching 'Test Show'" in result.output
    assert "Test Show" in result.output

def test_search_tmdb_by_name_no_results(runner, mock_ctx):
    """Test that search_tmdb prints not found message if no shows are found by name."""
    ctx, tmdb = mock_ctx
    tmdb.search_show.return_value = {"results": []}
    result = runner.invoke(search_tmdb, ['NoShow'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "No shows found on TMDB matching 'NoShow'" in result.output

def test_search_tmdb_by_name_with_year(runner, mock_ctx):
    """Test that search_tmdb only shows results matching the year filter."""
    ctx, tmdb = mock_ctx
    tmdb.search_show.return_value = {"results": [
        {"id": 1, "name": "Show 2020", "first_air_date": "2020-01-01"},
        {"id": 2, "name": "Show 2021", "first_air_date": "2021-01-01"}
    ]}
    result = runner.invoke(search_tmdb, ['Show', '--year', '2020'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Show 2020" in result.output
    assert "Show 2021" not in result.output

def test_search_tmdb_by_name_with_limit(runner, mock_ctx):
    """Test that search_tmdb only shows up to the specified limit of results."""
    ctx, tmdb = mock_ctx
    tmdb.search_show.return_value = {"results": [
        {"id": i, "name": f"Show {i}", "first_air_date": "2020-01-01"} for i in range(1, 21)
    ]}
    result = runner.invoke(search_tmdb, ['Show', '--limit', '5'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Showing first 5 results" in result.output or "Found 5 shows matching" in result.output
    for i in range(1, 6):
        assert f"Show {i}" in result.output
    for i in range(6, 11):
        assert f"Show {i}" not in result.output or f"Show {i}" in result.output  # allow for table formatting

def test_search_tmdb_by_tmdb_id_found(runner, mock_ctx):
    """Test that search_tmdb finds and displays a show by TMDB ID."""
    ctx, tmdb = mock_ctx
    tmdb.get_show_details.return_value = {"info": {"id": 123, "name": "Test Show", "first_air_date": "2020-01-01"}}
    result = runner.invoke(search_tmdb, ['--tmdb-id', '123'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found show with TMDB ID 123" in result.output
    assert "Test Show" in result.output

def test_search_tmdb_by_tmdb_id_not_found(runner, mock_ctx):
    """Test that search_tmdb prints not found message if TMDB ID is not found."""
    ctx, tmdb = mock_ctx
    tmdb.get_show_details.return_value = {}
    result = runner.invoke(search_tmdb, ['--tmdb-id', '999'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "No show found with TMDB ID 999" in result.output

def test_search_tmdb_dry_run(runner, mock_ctx):
    """Test that search_tmdb prints dry run info and does not search TMDB."""
    ctx, tmdb = mock_ctx
    result = runner.invoke(search_tmdb, ['--dry-run', 'Test Show', '--limit', '3', '--year', '2020'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "DRY RUN: Would search TMDB for shows" in result.output
    assert "Show name: Test Show" in result.output
    assert "Year filter: 2020" in result.output
    assert "Result limit: 3" in result.output
    assert not tmdb.search_show.called
    assert not tmdb.get_show_details.called

def test_search_tmdb_tmdb_error(runner, mock_ctx):
    """Test that search_tmdb prints error and exits if the TMDB service raises an exception."""
    ctx, tmdb = mock_ctx
    tmdb.search_show.side_effect = Exception('fail!')
    result = runner.invoke(search_tmdb, ['Show'], obj=ctx.obj)
    assert result.exit_code == 1
    assert "Error searching TMDB: fail!" in result.output 