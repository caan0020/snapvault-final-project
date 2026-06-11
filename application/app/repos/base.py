"""Repository interface shared by the DynamoDB and local backends.

Keeping the same five operations on both sides means the route handlers
never care which database is behind them.
"""
from abc import ABC, abstractmethod


class Repo(ABC):
    @abstractmethod
    def list(self):
        """Return all items, newest first."""

    @abstractmethod
    def get(self, id):
        """Return a single item by id, or None."""

    @abstractmethod
    def save(self, obj):
        """Insert or overwrite an item; returns it."""

    @abstractmethod
    def delete(self, id):
        """Delete an item by id (no error if missing)."""

    @abstractmethod
    def find_by(self, field, value):
        """Return all items whose `field` equals `value`, newest first."""
