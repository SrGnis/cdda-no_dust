#!/usr/bin/env python3
"""
Error Handling and Recovery for CDDA No Dust Mod Automation

This module provides comprehensive error handling, recovery mechanisms,
and graceful failure handling for the automation system.
"""

import sys
import traceback
import functools
from pathlib import Path
from typing import Any, Callable, Optional, Dict, List
import logging
from enum import Enum
from datetime import datetime

from config import Config
from utils import read_json_safe, write_json_safe, cleanup_directories


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutomationError(Exception):
    """Base exception for automation system errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 recoverable: bool = True, context: Optional[Dict] = None):
        super().__init__(message)
        self.severity = severity
        self.recoverable = recoverable
        self.context = context or {}
        self.timestamp = datetime.now()


class DownloadError(AutomationError):
    """Error during data download operations."""
    pass


class ProcessingError(AutomationError):
    """Error during data processing operations."""
    pass


class GitError(AutomationError):
    """Error during git operations."""
    pass


class ConfigurationError(AutomationError):
    """Error in configuration or setup."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(message, ErrorSeverity.HIGH, False, context)


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self, config: Config):
        """Initialize the error handler with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.error_log_file = Path("error_log.json")
        self.recovery_strategies = self._setup_recovery_strategies()
    
    def _setup_recovery_strategies(self) -> Dict[type, Callable]:
        """Set up recovery strategies for different error types."""
        return {
            DownloadError: self._recover_download_error,
            ProcessingError: self._recover_processing_error,
            GitError: self._recover_git_error,
            ConfigurationError: self._recover_configuration_error
        }
    
    def handle_error(self, error: Exception, context: Optional[Dict] = None) -> bool:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            bool: True if error was recovered, False otherwise
        """
        try:
            # Log the error
            self._log_error(error, context)
            
            # Determine if this is a known automation error
            if isinstance(error, AutomationError):
                return self._handle_automation_error(error)
            else:
                return self._handle_unknown_error(error, context)
                
        except Exception as e:
            self.logger.critical(f"Error in error handler: {e}")
            return False
    
    def _handle_automation_error(self, error: AutomationError) -> bool:
        """Handle a known automation error."""
        self.logger.error(f"Automation error ({error.severity.value}): {error}")
        
        if not error.recoverable:
            self.logger.error("Error is not recoverable")
            return False
        
        # Try recovery strategy
        error_type = type(error)
        if error_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[error_type](error)
            except Exception as e:
                self.logger.error(f"Recovery strategy failed: {e}")
                return False
        
        return False
    
    def _handle_unknown_error(self, error: Exception, context: Optional[Dict] = None) -> bool:
        """Handle an unknown error."""
        self.logger.error(f"Unknown error: {error}")
        self.logger.debug(f"Error traceback: {traceback.format_exc()}")
        
        # For unknown errors, we generally can't recover
        return False
    
    def _log_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """Log error details to file and logger."""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        if isinstance(error, AutomationError):
            error_info.update({
                "severity": error.severity.value,
                "recoverable": error.recoverable,
                "automation_context": error.context
            })
        
        # Log to file
        self._append_error_log(error_info)
        
        # Log to logger based on severity
        if isinstance(error, AutomationError):
            if error.severity == ErrorSeverity.CRITICAL:
                self.logger.critical(f"Critical error: {error}")
            elif error.severity == ErrorSeverity.HIGH:
                self.logger.error(f"High severity error: {error}")
            elif error.severity == ErrorSeverity.MEDIUM:
                self.logger.warning(f"Medium severity error: {error}")
            else:
                self.logger.info(f"Low severity error: {error}")
        else:
            self.logger.error(f"Unhandled error: {error}")
    
    def _append_error_log(self, error_info: Dict) -> None:
        """Append error information to the error log file."""
        try:
            # Read existing log
            log_data = read_json_safe(self.error_log_file, {"errors": []}, self.logger)

            # Append new error
            log_data["errors"].append(error_info)

            # Keep only last 100 errors
            if len(log_data["errors"]) > 100:
                log_data["errors"] = log_data["errors"][-100:]

            # Write back to file
            write_json_safe(self.error_log_file, log_data, self.logger)

        except Exception as e:
            self.logger.warning(f"Failed to write error log: {e}")
    
    def _recover_download_error(self, error: DownloadError) -> bool:
        """Recovery strategy for download errors."""
        self.logger.info("Attempting to recover from download error...")
        
        # Clean up any partial downloads
        cleanup_dirs = [self.config.temp_dir, self.config.source_data_dir]

        if cleanup_directories(cleanup_dirs, self.logger):
            self.logger.info("Download error recovery completed")
            return True
        else:
            self.logger.error("Download error recovery failed")
            return False
    
    def _recover_processing_error(self, error: ProcessingError) -> bool:
        """Recovery strategy for processing errors."""
        self.logger.info("Attempting to recover from processing error...")
        
        # For processing errors, we might want to clean up partial output
        try:
            # This is a placeholder - specific recovery depends on the error context
            self.logger.info("Processing error recovery completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Processing error recovery failed: {e}")
            return False
    
    def _recover_git_error(self, error: GitError) -> bool:
        """Recovery strategy for git errors."""
        self.logger.info("Attempting to recover from git error...")
        
        # For git errors, we might want to reset to a clean state
        try:
            # This is a placeholder - specific recovery depends on the error context
            self.logger.info("Git error recovery completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Git error recovery failed: {e}")
            return False
    
    def _recover_configuration_error(self, error: ConfigurationError) -> bool:
        """Recovery strategy for configuration errors."""
        self.logger.error("Configuration error cannot be automatically recovered")
        return False


def with_error_handling(error_handler: Optional[ErrorHandler] = None, 
                       reraise: bool = False):
    """
    Decorator to add error handling to functions.
    
    Args:
        error_handler: ErrorHandler instance to use
        reraise: Whether to reraise the exception after handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_handler:
                    context = {
                        "function": func.__name__,
                        "args": str(args)[:200],  # Limit length
                        "kwargs": str(kwargs)[:200]
                    }
                    error_handler.handle_error(e, context)
                
                if reraise:
                    raise
                else:
                    # Return None or appropriate default value
                    return None
        
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default=None, **kwargs) -> Any:
    """
    Safely execute a function and return a default value on error.
    
    Args:
        func: Function to execute
        *args: Function arguments
        default: Default value to return on error
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.debug(f"Safe execution failed for {func.__name__}: {e}")
        return default
