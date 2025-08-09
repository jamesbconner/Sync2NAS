import json
import click
import sqlite3
from typing import Optional
from click import echo
from cli.main import sync2nas_cli


@sync2nas_cli.command()
@click.option("--db-file", type=click.Path(exists=True), required=False, help="Path to SQLite DB (overrides config)")
@click.option("--source-table", default="downloaded_files_v0", show_default=True, help="Legacy source table name")
@click.option("--target-table", default="downloaded_files", show_default=True, help="Target table name")
@click.option("--limit", type=int, default=0, show_default=True, help="Limit rows to migrate (0 = no limit)")
@click.pass_context
def migrate_downloaded_files(ctx: click.Context, db_file: Optional[str], source_table: str, target_table: str, limit: int) -> None:
    """Migrate legacy records from a source table into the new downloaded_files table (SQLite only)."""
    cfg = ctx.obj["config"]
    if not db_file:
        # Use configured SQLite DB file
        if cfg.get("Database", "type", fallback="sqlite").lower() != "sqlite":
            raise click.ClickException("This migration utility currently supports SQLite only.")
        db_file = cfg.get("SQLite", "db_file")
    echo(f"Using SQLite DB: {db_file}")

    def dict_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    conn = sqlite3.connect(db_file)
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # Ensure target table exists
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (target_table,))
    if not cur.fetchone():
        raise click.ClickException(f"Target table '{target_table}' does not exist. Initialize the database first.")

    # Build SELECT from legacy table
    select_sql = f"SELECT * FROM {source_table}"
    if limit and limit > 0:
        select_sql += f" LIMIT {int(limit)}"

    try:
        rows = cur.execute(select_sql).fetchall()
    except sqlite3.Error as e:
        raise click.ClickException(f"Failed to read from source table '{source_table}': {e}")

    migrated = 0
    for row in rows:
        # Column mapping with sensible defaults
        name = row.get("name")
        # Legacy likely used 'path' for remote/original; map to both columns
        remote_path = row.get("path")
        current_path = row.get("current_path")
        previous_path = row.get("previous_path")
        size = row.get("size", 0)
        modified_time = row.get("modified_time")
        fetched_at = row.get("fetched_at")
        is_dir = int(row.get("is_dir", 0))
        status = row.get("status", "downloaded")
        file_type = row.get("file_type", "unknown")
        file_hash_value = row.get("file_hash_value")
        file_hash_algo = row.get("file_hash_algo")
        hash_calculated_at = row.get("hash_calculated_at")
        show_name = row.get("show_name")
        season = row.get("season")
        episode = row.get("episode")
        confidence = row.get("confidence")
        reasoning = row.get("reasoning")
        tmdb_id = row.get("tmdb_id")
        routing_attempts = row.get("routing_attempts", 0)
        last_routing_attempt = row.get("last_routing_attempt")
        error_message = row.get("error_message")
        metadata = row.get("metadata")
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)

        if not name or not remote_path:
            # Skip malformed legacy rows
            continue

        try:
            cur.execute(
                f"""
                INSERT INTO {target_table} (
                    name, path, remote_path, current_path, previous_path,
                    size, modified_time, fetched_at, is_dir,
                    status, file_type, file_hash_value, file_hash_algo, hash_calculated_at,
                    show_name, season, episode, confidence, reasoning, tmdb_id,
                    routing_attempts, last_routing_attempt, error_message, metadata
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(remote_path) DO UPDATE SET
                    name=excluded.name,
                    path=excluded.path,
                    current_path=COALESCE(excluded.current_path, {target_table}.current_path),
                    previous_path=COALESCE(excluded.previous_path, {target_table}.previous_path),
                    size=excluded.size,
                    modified_time=excluded.modified_time,
                    fetched_at=excluded.fetched_at,
                    is_dir=excluded.is_dir,
                    status=excluded.status,
                    file_type=excluded.file_type,
                    file_hash_value=COALESCE(excluded.file_hash_value, {target_table}.file_hash_value),
                    file_hash_algo=COALESCE(excluded.file_hash_algo, {target_table}.file_hash_algo),
                    hash_calculated_at=COALESCE(excluded.hash_calculated_at, {target_table}.hash_calculated_at),
                    show_name=excluded.show_name,
                    season=excluded.season,
                    episode=excluded.episode,
                    confidence=excluded.confidence,
                    reasoning=excluded.reasoning,
                    tmdb_id=excluded.tmdb_id,
                    routing_attempts=excluded.routing_attempts,
                    last_routing_attempt=COALESCE(excluded.last_routing_attempt, {target_table}.last_routing_attempt),
                    error_message=COALESCE(excluded.error_message, {target_table}.error_message),
                    metadata=COALESCE(excluded.metadata, {target_table}.metadata)
                """,
                (
                    name,
                    remote_path,  # path (legacy)
                    remote_path,
                    current_path,
                    previous_path,
                    size,
                    modified_time,
                    fetched_at,
                    is_dir,
                    status,
                    file_type,
                    file_hash_value,
                    file_hash_algo,
                    hash_calculated_at,
                    show_name,
                    season,
                    episode,
                    confidence,
                    reasoning,
                    tmdb_id,
                    routing_attempts,
                    last_routing_attempt,
                    error_message,
                    metadata,
                ),
            )
            migrated += 1
        except sqlite3.Error as e:
            echo(f"Skipping row due to error: {e}")

    conn.commit()
    conn.close()
    echo(f"Migrated {migrated} rows from {source_table} to {target_table}")


