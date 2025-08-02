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
    db_type = config["Database"]["type"].lower()
    
    if db_type == "sqlite":
        return SQLiteDBService(config["SQLite"]["db_file"], read_only=read_only)
    
    elif db_type == "postgres":
        return PostgresDBService(
            f"postgresql://{config['PostgreSQL']['user']}:{config['PostgreSQL']['password']}"
            f"@{config['PostgreSQL']['host']}:{config['PostgreSQL']['port']}"
            f"/{config['PostgreSQL']['database']}",
            read_only=read_only
        )
    
    elif db_type == "milvus":
        return MilvusDBService(
            host=config["Milvus"]["host"],
            port=config["Milvus"]["port"],
            read_only=read_only
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}") 