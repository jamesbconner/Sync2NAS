# Dependency injection setup for Sync2NAS FastAPI application
# Provides functions to initialize and retrieve core services for API endpoints

from fastapi import Depends, Request
from services.db_factory import create_db_service
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService
from api.services.show_service import ShowService
from api.services.file_service import FileService
from api.services.remote_service import RemoteService
from api.services.admin_service import AdminService
from services.llm_factory import create_llm_service, setup_llm_caching_and_tracing


def get_services(config):
    """
    Initialize and return all core services as a dictionary.
    This is called once at API startup and attached to app.state.services.
    
    Includes comprehensive validation for all services, especially LLM configuration.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    db = create_db_service(config)
    sftp = SFTPService(
        config["SFTP"]["host"], 
        int(config["SFTP"]["port"]), 
        config["SFTP"]["username"], 
        config["SFTP"]["ssh_key_path"]
    )
    tmdb = TMDBService(config["TMDB"]["api_key"])
    
    anime_tv_path = config["Routing"]["anime_tv_path"]
    incoming_path = config["Transfers"]["incoming"]
    
    # Create and validate LLM service with comprehensive error handling
    llm_service = None
    llm_chains = None
    
    try:
        # Validate configuration and create LLM service in one step (efficient)
        from services.llm_factory import validate_and_create_llm_service
        logger.info("Validating LLM configuration and creating service...")
        llm_service = validate_and_create_llm_service(config)
        logger.info("✓ LLM service validated and created successfully")
        
        # Setup caching and tracing
        setup_llm_caching_and_tracing(config)
        logger.info("✓ LLM caching and tracing configured")
        
        # Step 4: Initialize LLM Chain Service
        from services.llm_chain_service import LLMChainService
        llm_chains = LLMChainService(llm_service)
        logger.info("✓ LLM chains service initialized")
        
        # Step 5: Validate with test operation
        logger.info("Testing LLM service with sample parse...")
        test_result = llm_chains.parse_filename("Test.Show.S01E01.mkv")
        
        if not test_result:
            raise Exception("LLM service test returned no result")
        
        if not hasattr(test_result, 'confidence'):
            raise Exception("LLM service test returned invalid result format")
        
        logger.info(f"✓ LLM service test successful (confidence: {test_result.confidence:.2f})")
        
    except Exception as e:
        logger.error(f"❌ LLM service initialization failed: {e}")
        logger.error("💡 LLM service issues detected:")
        logger.error("   - Check your configuration file for the [llm] section")
        logger.error("   - Ensure the selected service (ollama/openai/anthropic) is properly configured")
        logger.error("   - Verify service connectivity and API keys")
        logger.error("   - API will continue without LLM functionality")
        
        # Set services to None to indicate unavailability
        llm_service = None
        llm_chains = None
    
    return {
        "db": db,
        "sftp": sftp,
        "tmdb": tmdb,
        "anime_tv_path": anime_tv_path,
        "incoming_path": incoming_path,
        "config": config,
        "llm_service": llm_service,
        "llm_chains": llm_chains
    }


def get_show_service(request: Request) -> ShowService:
    """
    Dependency for show service.
    Returns a ShowService instance for use in show-related endpoints.
    """
    services = request.app.state.services
    return ShowService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"]
    )


def get_file_service(request: Request) -> FileService:
    """
    Dependency for file service.
    Returns a FileService instance for use in file-related endpoints.
    """
    services = request.app.state.services
    return FileService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"],
        services["incoming_path"],
        services["llm_chains"]
    )


def get_remote_service(request: Request) -> RemoteService:
    """
    Dependency for remote service.
    Returns a RemoteService instance for use in remote/SFTP-related endpoints.
    """
    services = request.app.state.services
    return RemoteService(
        services["sftp"],
        services["db"],
        services["config"]
    )


def get_admin_service(request: Request) -> AdminService:
    """
    Dependency for admin service.
    Returns an AdminService instance for use in admin-related endpoints.
    """
    services = request.app.state.services
    return AdminService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"],
        services["config"]
    )


def get_llm_service(request: Request):
    """
    Dependency for LLM service.
    Returns the LLM service instance for use in endpoints that require LLM parsing.
    """
    services = request.app.state.services
    return services["llm_service"] 


def get_llm_chains_service(request: Request):
    """
    Dependency for LLM chains service.
    Returns the LLM chains service instance for use in endpoints that require LLM parsing.
    """
    services = request.app.state.services
    return services["llm_chains"]


def get_db_service(request: Request):
    """Dependency for direct DB service access in endpoints."""
    services = request.app.state.services
    return services["db"]