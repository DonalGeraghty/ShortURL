"""
Logging configuration for URL Shortener API
Supports different environments (development, production, Google Cloud Run)
"""

import os
import logging
from datetime import datetime

# Environment-based logging configuration
def get_logging_config(environment=None):
    """
    Get logging configuration based on environment
    
    Args:
        environment (str): Environment name ('development', 'production', 'cloud_run')
    
    Returns:
        dict: Logging configuration
    """
    if not environment:
        environment = os.environ.get('FLASK_ENV', 'production')
    
    # Base configuration
    base_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'structured': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'stream': 'ext://sys.stdout'
            },
            'error_file': {
                'class': 'logging.FileHandler',
                'level': 'ERROR',
                'formatter': 'structured',
                'filename': 'logs/errors.log',
                'mode': 'a'
            },
            'access_file': {
                'class': 'logging.FileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': 'logs/access.log',
                'mode': 'a'
            }
        },
        'loggers': {
            'url_shortener': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'flask_app': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'werkzeug': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    
    # Environment-specific overrides
    if environment == 'development':
        base_config['handlers']['console']['level'] = 'DEBUG'
        base_config['handlers']['console']['formatter'] = 'detailed'
        base_config['loggers']['url_shortener']['level'] = 'DEBUG'
        base_config['loggers']['flask_app']['level'] = 'DEBUG'
        base_config['root']['level'] = 'DEBUG'
        
    elif environment == 'cloud_run':
        # Google Cloud Run specific configuration
        base_config['handlers']['console']['formatter'] = 'structured'
        base_config['loggers']['url_shortener']['level'] = 'INFO'
        base_config['loggers']['flask_app']['level'] = 'INFO'
        base_config['root']['level'] = 'WARNING'
        
    elif environment == 'production':
        # Production configuration with file logging
        base_config['handlers']['console']['level'] = 'WARNING'
        base_config['loggers']['url_shortener']['handlers'] = ['console', 'error_file']
        base_config['loggers']['flask_app']['handlers'] = ['console', 'access_file']
        base_config['root']['level'] = 'WARNING'
    
    return base_config

def setup_logging(environment=None):
    """
    Set up logging configuration
    
    Args:
        environment (str): Environment name
    
    Returns:
        logging.Logger: Configured logger
    """
    import logging.config
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Get configuration
    config = get_logging_config(environment)
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Get logger
    logger = logging.getLogger('url_shortener')
    
    # Log configuration applied
    logger.info("Logging configuration applied", extra={
        "operation": "logging_setup",
        "environment": environment or os.environ.get('FLASK_ENV', 'production'),
        "log_level": logger.level,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return logger

def get_logger(name, environment=None):
    """
    Get a configured logger by name
    
    Args:
        name (str): Logger name
        environment (str): Environment name
    
    Returns:
        logging.Logger: Configured logger
    """
    if not environment:
        environment = os.environ.get('FLASK_ENV', 'production')
    
    # Set up logging if not already configured
    if not logging.getLogger().handlers:
        setup_logging(environment)
    
    return logging.getLogger(name)

# Convenience functions for common loggers
def get_url_shortener_logger():
    """Get the URL shortener logger"""
    return get_logger('url_shortener')

def get_flask_app_logger():
    """Get the Flask app logger"""
    return get_logger('flask_app')

def get_access_logger():
    """Get the access logger for request/response logging"""
    return get_logger('access')

def get_error_logger():
    """Get the error logger for error tracking"""
    return get_logger('error')

# Log level utilities
def set_log_level(logger_name, level):
    """
    Set log level for a specific logger
    
    Args:
        logger_name (str): Name of the logger
        level (str): Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Log the change
    logger.info(f"Log level changed to {level.upper()}", extra={
        "operation": "log_level_change",
        "new_level": level.upper(),
        "timestamp": datetime.utcnow().isoformat()
    })

def enable_debug_logging():
    """Enable debug logging for development"""
    set_log_level('url_shortener', 'DEBUG')
    set_log_level('flask_app', 'DEBUG')
    set_log_level('root', 'DEBUG')

def enable_production_logging():
    """Enable production logging (INFO and above)"""
    set_log_level('url_shortener', 'INFO')
    set_log_level('flask_app', 'INFO')
    set_log_level('root', 'WARNING')

# Performance logging utilities
def log_performance(operation, duration_ms, **kwargs):
    """
    Log performance metrics
    
    Args:
        operation (str): Operation name
        duration_ms (float): Duration in milliseconds
        **kwargs: Additional context information
    """
    logger = get_url_shortener_logger()
    
    log_data = {
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "performance": True
    }
    
    # Add additional context
    log_data.update(kwargs)
    
    # Log based on performance thresholds
    if duration_ms < 100:
        logger.info("Operation completed quickly", extra=log_data)
    elif duration_ms < 500:
        logger.info("Operation completed normally", extra=log_data)
    elif duration_ms < 1000:
        logger.warning("Operation completed slowly", extra=log_data)
    else:
        logger.error("Operation completed very slowly", extra=log_data)

# Error logging utilities
def log_error(operation, error, **kwargs):
    """
    Log error information with context
    
    Args:
        operation (str): Operation name
        error (Exception): Error object
        **kwargs: Additional context information
    """
    logger = get_error_logger()
    
    log_data = {
        "operation": operation,
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": datetime.utcnow().isoformat(),
        "error": True
    }
    
    # Add additional context
    log_data.update(kwargs)
    
    logger.error("Operation failed", extra=log_data)
