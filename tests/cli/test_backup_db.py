import pytest
from click.testing import CliRunner
from cli.backup_db import backup_db
from unittest.mock import MagicMock, patch

@pytest.fixture
def runner():
    """Fixture providing a Click CliRunner instance."""
    return CliRunner()

@pytest.fixture
def mock_ctx():
    """Fixture providing a mock Click context with db_service and config."""
    db_service = MagicMock()
    config = {'Database': {'type': 'sqlite'}}
    ctx = MagicMock()
    ctx.obj = {'db': db_service, 'config': config, 'dry_run': False}
    return ctx, db_service

def test_backup_db_dry_run(runner, mock_ctx, caplog):
    """Test that backup_db logs dry run messages and does not call backup_database when dry_run is True in ctx.obj."""
    ctx, db_service = mock_ctx
    ctx.obj['dry_run'] = True
    with caplog.at_level('INFO'):
        result = runner.invoke(backup_db, [], obj=ctx.obj)
    assert result.exit_code == 0
    assert "[DRY RUN] Simulating database backup." in caplog.text
    assert not db_service.backup_database.called

def test_backup_db_success(runner, mock_ctx, caplog):
    """Test that backup_db calls backup_database and logs success when not a dry run."""
    ctx, db_service = mock_ctx
    ctx.obj['dry_run'] = False
    db_service.backup_database.return_value = '/tmp/backup.sqlite'
    with caplog.at_level('INFO'):
        result = runner.invoke(backup_db, [], obj=ctx.obj)
    assert result.exit_code == 0
    assert db_service.backup_database.called
    assert "Database backup created successfully: /tmp/backup.sqlite" in caplog.text

def test_backup_db_failure(runner, mock_ctx, caplog):
    """Test that backup_db logs an error if backup_database raises an exception."""
    ctx, db_service = mock_ctx
    ctx.obj['dry_run'] = False
    db_service.backup_database.side_effect = Exception('fail!')
    with caplog.at_level('ERROR'):
        result = runner.invoke(backup_db, [], obj=ctx.obj)
    assert result.exit_code == 0
    assert "Database backup failed: fail!" in caplog.text 