"""
This module provides a factory for creating database service instances based on configuration.
"""
from typing import Dict, Any
from services.db_implementations.db_interface import DatabaseInterface
from services.db_implementations.sqlite_implementation import SQLiteDBService
from services.db_implementations.postgres_implementation import PostgresDBService
from services.db_implementations.milvus_implementation import MilvusDBService

def create_db_service(config: Dict[str, Any], read_only: bool = False) -> DatabaseInterface:
    """
    Create and return the appropriate database service based on configuration.

    Args:
        config (Dict[str, Any]): Configuration dictionary containing database settings.
        read_only (bool): If True, create database in read-only mode.

    Returns:
        DatabaseInterface: An instance of the appropriate database service.

    Raises:
        ValueError: If the database type is not supported.
    """
    # Handle both normalized (lowercase) and raw (uppercase) section names
    database_section = config.get("database") or config.get("Database")
    if not database_section:
        raise ValueError("Database configuration section not found")
    
    db_type = database_section["type"].lower()
    
    if db_type == "sqlite":
        sqlite_section = config.get("sqlite") or config.get("SQLite")
        return SQLiteDBService(sqlite_section["db_file"], read_only=read_only)
    
    elif db_type == "postgres":
        postgres_section = config.get("postgresql") or config.get("PostgreSQL")
        return PostgresDBService(
            f"postgresql://{postgres_section['user']}:{postgres_section['password']}"
            f"@{postgres_section['host']}:{postgres_section['port']}"
            f"/{postgres_section['database']}",
            read_only=read_only
        )
    
    elif db_type == "milvus":
        milvus_section = config.get("milvus") or config.get("Milvus")
        return MilvusDBService(
            host=milvus_section["host"],
            port=milvus_section["port"],
            read_only=read_only
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}") 