"""
Conversation memory management for maintaining chat context.

This module provides a rolling buffer implementation that stores conversation
history with a configurable maximum size, automatically removing old messages
when the limit is reached.
"""

from collections import deque
from typing import Any


class RollingBuffer:
    """
    A fixed-size rolling buffer for conversation messages.

    This buffer maintains a conversation history with automatic removal
    of the oldest messages when the maximum size is reached. This helps
    control token usage and API costs while maintaining recent context.

    Attributes:
        buf: Internal deque storing the messages
        max_len: Maximum number of messages to store
    """

    def __init__(self, max_len: int = 12) -> None:
        """
        Initialize the rolling buffer.

        Args:
            max_len: Maximum number of messages to store (default: 12)
        """
        self.buf: deque[dict[str, Any]] = deque(maxlen=max_len)
        self.max_len = max_len

    def append(self, message: dict[str, Any]) -> None:
        """
        Add a single message to the buffer.

        If the buffer is full, the oldest message will be automatically
        removed to make room for the new one.

        Args:
            message: Message dictionary with 'role' and 'content' keys
        """
        self.buf.append(message)

    def extend(self, messages: list[dict[str, Any]]) -> None:
        """
        Add multiple messages to the buffer.

        Messages are added in order. If adding all messages would exceed
        the buffer size, older messages are removed automatically.

        Args:
            messages: List of message dictionaries to add
        """
        for message in messages:
            self.buf.append(message)

    def as_messages(self) -> list[dict[str, Any]]:
        """
        Get all messages in the buffer as a list.

        Returns:
            List of message dictionaries in chronological order
        """
        return list(self.buf)

    def clear(self) -> None:
        """Remove all messages from the buffer."""
        self.buf.clear()

    def __len__(self) -> int:
        """
        Get the current number of messages in the buffer.

        Returns:
            Number of messages currently stored
        """
        return len(self.buf)

    def __repr__(self) -> str:
        """
        Get string representation of the buffer.

        Returns:
            String showing buffer size and capacity
        """
        return f"RollingBuffer(size={len(self.buf)}, max={self.max_len})"