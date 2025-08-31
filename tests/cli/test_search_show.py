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
    """Fixture providing a mock Click context with db service."""
    db_service = MagicMock()
    tmdb_service = MagicMock()
    ctx = MagicMock()
    ctx.obj = {'db': db_service, 'tmdb': tmdb_service, 'dry_run': False}
    return ctx, db_service

def test_search_show_lists_all_shows(runner, mock_ctx, mock_llm_service_patch):
    """Test that running search_show with no arguments lists all shows in the database."""
    ctx, db_service = mock_ctx
    db_service.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    ]
    result = runner.invoke(search_show, [], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 shows in database" in result.output
    assert "Test Show" in result.output

def test_search_show_exact_match(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show finds and displays a show by exact name match."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found exact match for 'Test Show'" in result.output
    assert "Test Show" in result.output

def test_search_show_partial_match(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show finds and displays shows by partial name match when no exact match is found."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    ]
    result = runner.invoke(search_show, ['Test'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 partial match for 'Test'" in result.output or "Found 1 partial matches for 'Test'" in result.output
    assert "Test Show" in result.output

def test_search_show_no_match_offers_tmdb(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show offers TMDB search if no matches are found and user declines."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = []
    with patch('click.confirm', return_value=False):
        result = runner.invoke(search_show, ['NoShow'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "No shows found matching 'NoShow'" in result.output or "No exact match found for 'NoShow'" in result.output
    assert "Would you like to search TMDB for similar shows?" in result.output

def test_search_show_by_tmdb_id_found(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show finds and displays a show by TMDB ID."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_tmdb_id.return_value = {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    result = runner.invoke(search_show, ['--tmdb-id', '123'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found show with TMDB ID 123" in result.output
    assert "Test Show" in result.output

def test_search_show_by_tmdb_id_not_found(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show prints error and exits if TMDB ID is not found."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_tmdb_id.return_value = None
    result = runner.invoke(search_show, ['--tmdb-id', '999'], obj=ctx.obj)
    assert result.exit_code == 1
    assert "No show found with TMDB ID 999" in result.output

def test_search_show_dry_run(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show prints dry run info and does not search database."""
    ctx, db_service = mock_ctx
    ctx.obj['dry_run'] = True
    result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "🧪 DRY RUN: Would search for shows" in result.output
    assert "Show name: Test Show" in result.output
    assert not db_service.get_all_shows.called

def test_search_show_db_error(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show prints error and exits if the database call raises an exception."""
    ctx, db_service = mock_ctx
    db_service.get_all_shows.side_effect = Exception('fail!')
    result = runner.invoke(search_show, [], obj=ctx.obj)
    assert result.exit_code == 1
    assert "Error searching for shows: fail!" in result.output

# New tests to increase coverage

def test_search_show_no_context_object(runner, mock_llm_service_patch):
    """Test that search_show handles missing context object gracefully."""
    result = runner.invoke(search_show, ['Test Show'], obj=None)
    assert result.exit_code == 1
    assert "❌ Error: No context object found" in result.output

def test_search_show_dry_run_with_tmdb_id(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles dry run with TMDB ID."""
    ctx, db_service = mock_ctx
    ctx.obj['dry_run'] = True
    result = runner.invoke(search_show, ['--tmdb-id', '123'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "🧪 DRY RUN: Would search for shows" in result.output
    assert "TMDB ID: 123" in result.output
    assert not db_service.get_show_by_tmdb_id.called

def test_search_show_multiple_partial_matches(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show displays multiple partial matches in a table."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show 1', 'sys_name': 'Test_Show_1', 'sys_path': '/shows/Test_Show_1', 'tmdb_status': 'Ended'},
        {'id': 2, 'tmdb_id': 456, 'tmdb_name': 'Test Show 2', 'sys_name': 'Test_Show_2', 'sys_path': '/shows/Test_Show_2', 'tmdb_status': 'Running'}
    ]
    result = runner.invoke(search_show, ['Test'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 2 partial matches for 'Test'" in result.output
    assert "Test Show 1" in result.output
    assert "Test Show 2" in result.output

def test_search_show_exact_match_with_verbose(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show displays verbose information when --verbose flag is used."""
    ctx, db_service = mock_ctx
    show_data = {
        'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 
        'sys_path': '/shows/Test_Show', 'aliases': 'Alias', 'tmdb_first_aired': '2020-01-01',
        'tmdb_last_aired': '2023-01-01', 'tmdb_year': 2020, 'tmdb_season_count': 3,
        'tmdb_episode_count': 30, 'tmdb_status': 'Ended', 'fetched_at': '2023-01-01',
        'tmdb_overview': 'A test show overview'
    }
    db_service.get_show_by_name_or_alias.return_value = show_data
    result = runner.invoke(search_show, ['Test Show', '--verbose'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found exact match for 'Test Show'" in result.output
    assert "Detailed Information" in result.output
    assert "First Aired: 2020-01-01" in result.output
    assert "Last Aired: 2023-01-01" in result.output
    assert "Year: 2020" in result.output
    assert "Seasons: 3" in result.output
    assert "Episodes: 30" in result.output
    assert "Status: Ended" in result.output
    assert "Overview:" in result.output

def test_search_show_exact_match_with_verbose_no_dates(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles missing date fields in verbose mode."""
    ctx, db_service = mock_ctx
    show_data = {
        'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 
        'sys_path': '/shows/Test_Show', 'aliases': 'Alias'
    }
    db_service.get_show_by_name_or_alias.return_value = show_data
    result = runner.invoke(search_show, ['Test Show', '--verbose'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found exact match for 'Test Show'" in result.output
    assert "First Aired: N/A" in result.output
    assert "Last Aired: N/A" in result.output

def test_search_show_exact_match_with_verbose_datetime_objects(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles datetime objects in verbose mode."""
    from datetime import datetime
    ctx, db_service = mock_ctx
    show_data = {
        'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 
        'sys_path': '/shows/Test_Show', 'aliases': 'Alias', 
        'tmdb_first_aired': datetime(2020, 1, 1),
        'tmdb_last_aired': datetime(2023, 1, 1)
    }
    db_service.get_show_by_name_or_alias.return_value = show_data
    result = runner.invoke(search_show, ['Test Show', '--verbose'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "First Aired: 2020-01-01" in result.output
    assert "Last Aired: 2023-01-01" in result.output

def test_search_show_exact_match_with_verbose_complex_date_strings(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles complex date strings in verbose mode."""
    ctx, db_service = mock_ctx
    show_data = {
        'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 
        'sys_path': '/shows/Test_Show', 'aliases': 'Alias', 
        'tmdb_first_aired': '2020-01-01T12:00:00Z',
        'tmdb_last_aired': '2023-01-01 15:30:00'
    }
    db_service.get_show_by_name_or_alias.return_value = show_data
    result = runner.invoke(search_show, ['Test Show', '--verbose'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "First Aired: 2020-01-01" in result.output
    assert "Last Aired: 2023-01-01" in result.output

def test_search_show_exact_match_with_verbose_date_exception(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles date parsing exceptions in verbose mode."""
    ctx, db_service = mock_ctx
    show_data = {
        'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 
        'sys_path': '/shows/Test_Show', 'aliases': 'Alias', 
        'tmdb_first_aired': 'invalid-date',
        'tmdb_last_aired': 'invalid-date'
    }
    db_service.get_show_by_name_or_alias.return_value = show_data
    result = runner.invoke(search_show, ['Test Show', '--verbose'], obj=ctx.obj)
    assert result.exit_code == 0
    # The current implementation passes through strings that don't contain 'T' or ' '
    assert "First Aired: invalid-date" in result.output
    assert "Last Aired: invalid-date" in result.output

def test_search_show_exact_match_only(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show uses exact matching only when --exact flag is used."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = None
    with patch('click.confirm', return_value=False):
        result = runner.invoke(search_show, ['Test', '--exact'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "No exact match found for 'Test'" in result.output
    assert "Would you like to search TMDB for similar shows?" in result.output
    # Should not call get_all_shows for partial matching
    assert not db_service.get_all_shows.called

def test_search_show_tmdb_search_accepted(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show performs TMDB search when user accepts."""
    ctx, db_service = mock_ctx
    tmdb_service = ctx.obj['tmdb']
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = []
    tmdb_service.search_show.return_value = {
        'results': [
            {'id': 123, 'name': 'Test Show', 'first_air_date': '2020-01-01', 'overview': 'A test show'}
        ]
    }
    with patch('click.confirm', return_value=True):
        result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 similar shows on TMDB" in result.output
    assert "Test Show" in result.output
    assert "Tip: Use 'add-show' command with --tmdb-id to add any of these shows" in result.output

def test_search_show_tmdb_search_no_results(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles TMDB search with no results."""
    ctx, db_service = mock_ctx
    tmdb_service = ctx.obj['tmdb']
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = []
    tmdb_service.search_show.return_value = {'results': []}
    with patch('click.confirm', return_value=True):
        result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "No TMDB results found" in result.output

def test_search_show_tmdb_search_error(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles TMDB search errors."""
    ctx, db_service = mock_ctx
    tmdb_service = ctx.obj['tmdb']
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = []
    tmdb_service.search_show.side_effect = Exception('TMDB API error')
    with patch('click.confirm', return_value=True):
        result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Error searching TMDB: TMDB API error" in result.output

def test_search_show_tmdb_search_limited_results(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show limits TMDB results to 10."""
    ctx, db_service = mock_ctx
    tmdb_service = ctx.obj['tmdb']
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = []
    # Create 15 results
    results = []
    for i in range(15):
        results.append({
            'id': i, 
            'name': f'Test Show {i}', 
            'first_air_date': '2020-01-01', 
            'overview': f'Overview for show {i}'
        })
    tmdb_service.search_show.return_value = {'results': results}
    with patch('click.confirm', return_value=True):
        result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 15 similar shows on TMDB" in result.output
    # Should only show first 10 results in table
    assert "Test Show 0" in result.output
    assert "Test Show 9" in result.output
    # Should not show the 11th result
    assert "Test Show 10" not in result.output

def test_search_show_tmdb_search_with_long_overview(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show truncates long overviews in TMDB results."""
    ctx, db_service = mock_ctx
    tmdb_service = ctx.obj['tmdb']
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = []
    long_overview = "A" * 150  # 150 characters
    tmdb_service.search_show.return_value = {
        'results': [
            {'id': 123, 'name': 'Test Show', 'first_air_date': '2020-01-01', 'overview': long_overview}
        ]
    }
    with patch('click.confirm', return_value=True):
        result = runner.invoke(search_show, ['Test Show'], obj=ctx.obj)
    assert result.exit_code == 0
    # The overview should be truncated, but the exact format might vary due to table rendering
    # Just check that the long overview is not present in full
    assert "A" * 150 not in result.output  # Full 150-char overview should not be present
    assert "Test Show" in result.output  # Show name should be present

def test_search_show_empty_database(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show handles empty database gracefully."""
    ctx, db_service = mock_ctx
    db_service.get_all_shows.return_value = []
    result = runner.invoke(search_show, [], obj=ctx.obj)
    assert result.exit_code == 0
    assert "📭 No shows found in database" in result.output

def test_search_show_partial_match_with_aliases(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show finds matches in aliases field."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Full Show Name', 'sys_name': 'Full_Show_Name', 'sys_path': '/shows/Full_Show_Name', 'aliases': 'Short Name, SN'}
    ]
    result = runner.invoke(search_show, ['Short'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 partial match for 'Short'" in result.output
    assert "Full Show Name" in result.output

def test_search_show_partial_match_case_insensitive(runner, mock_ctx, mock_llm_service_patch):
    """Test that search_show performs case-insensitive partial matching."""
    ctx, db_service = mock_ctx
    db_service.get_show_by_name_or_alias.return_value = None
    db_service.get_all_shows.return_value = [
        {'id': 1, 'tmdb_id': 123, 'tmdb_name': 'Test Show', 'sys_name': 'Test_Show', 'sys_path': '/shows/Test_Show', 'aliases': 'Alias'}
    ]
    result = runner.invoke(search_show, ['test'], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Found 1 partial match for 'test'" in result.output
    assert "Test Show" in result.output 