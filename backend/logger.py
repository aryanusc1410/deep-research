"""
Logging utilities for the Deep Research Agent application.

This module provides consistent logging functionality across the application,
with proper formatting and flushing for different contexts.
"""

import sys
from typing import Any


class Logger:
    """
    Application logger with support for force-flushing in threaded contexts.
    
    This logger is designed to work correctly in both synchronous and
    threaded execution contexts, ensuring logs are visible immediately.
    """

    def __init__(self, prefix: str = ""):
        """
        Initialize the logger.

        Args:
            prefix: Optional prefix to prepend to all log messages
        """
        self.prefix = prefix

    def _format_message(self, component: str, message: str) -> str:
        """
        Format a log message with prefix and component.

        Args:
            component: The component/module generating the log
            message: The log message

        Returns:
            Formatted log message string
        """
        if self.prefix:
            return f"[{self.prefix}] [{component}] {message}"
        return f"[{component}] {message}"

    def info(self, component: str, message: str, force_flush: bool = False) -> None:
        """
        Log an info-level message.

        Args:
            component: The component/module generating the log
            message: The log message
            force_flush: Whether to force flush stdout (needed in thread pools)
        """
        print(self._format_message(component, message))
        if force_flush:
            sys.stdout.flush()

    def warning(self, component: str, message: str, force_flush: bool = False) -> None:
        """
        Log a warning-level message.

        Args:
            component: The component/module generating the log
            message: The warning message
            force_flush: Whether to force flush stdout
        """
        formatted = f"⚠️  {self._format_message(component, message)}"
        print(formatted)
        if force_flush:
            sys.stdout.flush()

    def error(self, component: str, message: str, force_flush: bool = False) -> None:
        """
        Log an error-level message.

        Args:
            component: The component/module generating the log
            message: The error message
            force_flush: Whether to force flush stdout
        """
        formatted = f"❌ {self._format_message(component, message)}"
        print(formatted)
        if force_flush:
            sys.stdout.flush()

    def success(self, component: str, message: str, force_flush: bool = False) -> None:
        """
        Log a success message.

        Args:
            component: The component/module generating the log
            message: The success message
            force_flush: Whether to force flush stdout
        """
        formatted = f"✅ {self._format_message(component, message)}"
        print(formatted)
        if force_flush:
            sys.stdout.flush()

    def debug(self, component: str, message: str, data: Any = None, force_flush: bool = False) -> None:
        """
        Log a debug-level message with optional data.

        Args:
            component: The component/module generating the log
            message: The debug message
            data: Optional data to include in the log
            force_flush: Whether to force flush stdout
        """
        formatted = self._format_message(component, message)
        if data is not None:
            formatted += f" | Data: {data}"
        print(formatted)
        if force_flush:
            sys.stdout.flush()


# Global logger instance
logger = Logger()


def log(message: str, force_flush: bool = False) -> None:
    """
    Simple logging function for backward compatibility.

    Args:
        message: The message to log
        force_flush: Whether to force flush stdout
    """
    print(message)
    if force_flush:
        sys.stdout.flush()