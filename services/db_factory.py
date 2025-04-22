from typing import Dict, Any
from db_implementations.db_interface import DatabaseInterface
from db_implementations.sqlite_implementation import SQLiteDBService
from db_implementations.postgres_implementation import PostgresDBService
from db_implementations.milvus_implementation import MilvusDBService

def create_db_service(config: Dict[str, Any]) -> DatabaseInterface:
    """Create and return the appropriate database service based on configuration.
    
    Args:
        config: Configuration dictionary containing database settings
        
    Returns:
        DatabaseInterface: An instance of the appropriate database service
        
    Raises:
        ValueError: If the database type is not supported
    """
    db_type = config["Database"]["type"].lower()
    
    if db_type == "sqlite":
        return SQLiteDBService(config["SQLite"]["db_file"])
    
    elif db_type == "postgres":
        return PostgresDBService(
            f"postgresql://{config['PostgreSQL']['user']}:{config['PostgreSQL']['password']}"
            f"@{config['PostgreSQL']['host']}:{config['PostgreSQL']['port']}"
            f"/{config['PostgreSQL']['database']}"
        )
    
    elif db_type == "milvus":
        return MilvusDBService(
            host=config["Milvus"]["host"],
            port=config["Milvus"]["port"]
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}") 