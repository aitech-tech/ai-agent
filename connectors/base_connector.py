"""
BaseConnector — all connectors must inherit from this class.
Provides common interface, retry logic, and error wrapping.
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds


class ConnectorError(Exception):
    """Raised when a connector operation fails."""
    def __init__(self, connector: str, message: str, status_code: int = None):
        self.connector = connector
        self.status_code = status_code
        super().__init__(f"[{connector}] {message}")


class AuthenticationError(ConnectorError):
    """Raised when authentication fails or tokens are missing."""
    pass


class BaseConnector(ABC):
    """
    Abstract base for all platform connectors.

    Subclasses must implement:
        authenticate() — set up credentials/tokens
        execute(action, params) — dispatch API calls

    Retry logic is provided by _execute_with_retry().
    """

    name: str = "base"  # Override in subclass

    def __init__(self, config: dict):
        self.config = config
        self._authenticated = False

    @abstractmethod
    def authenticate(self) -> dict:
        """
        Perform authentication flow.
        Returns a status dict: {"status": "ok"|"pending", "message": str, ...}
        """

    @abstractmethod
    def execute(self, action: str, params: dict) -> Any:
        """
        Execute a connector action.
        action: string name of the operation (e.g. "get_leads")
        params: dict of parameters for the action
        Returns structured data (list, dict, etc.)
        """

    def _execute_with_retry(self, fn, *args, **kwargs) -> Any:
        """Retry fn up to MAX_RETRIES times with exponential backoff."""
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except AuthenticationError:
                raise  # Don't retry auth errors
            except ConnectorError as e:
                last_exc = e
                if e.status_code and e.status_code < 500:
                    raise  # Don't retry 4xx client errors
                logger.warning(
                    "[%s] Attempt %d/%d failed: %s",
                    self.name, attempt, MAX_RETRIES, e
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF ** attempt)
            except Exception as e:
                last_exc = ConnectorError(self.name, str(e))
                logger.warning(
                    "[%s] Unexpected error attempt %d/%d: %s",
                    self.name, attempt, MAX_RETRIES, e
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF ** attempt)
        raise last_exc

    def health_check(self) -> dict:
        """Returns connector health. Override for custom checks."""
        return {"connector": self.name, "status": "ok", "authenticated": self._authenticated}
