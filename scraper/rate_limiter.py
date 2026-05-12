"""Token-bucket rate limiter with jitter and exponential backoff."""

import random
import time
from threading import Lock


class RateLimiter:
    """Token-bucket rate limiter with jitter for Reddit API compliance."""

    def __init__(self, requests_per_second: float = 1.0, jitter: tuple[float, float] = (0.5, 1.5)):
        self.min_interval = 1.0 / requests_per_second
        self.jitter = jitter
        self._last_request = 0.0
        self._lock = Lock()
        self._request_count = 0

    def wait(self):
        """Block until it's safe to make the next request."""
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request
            wait_time = self.min_interval - elapsed

            if wait_time > 0:
                jitter_factor = random.uniform(*self.jitter)
                total_wait = wait_time * jitter_factor
                time.sleep(total_wait)

            self._last_request = time.time()
            self._request_count += 1

    @property
    def request_count(self) -> int:
        return self._request_count

    def reset_count(self):
        self._request_count = 0


class BackoffHandler:
    """Exponential backoff for rate-limit (429) responses."""

    def __init__(self, base: int = 2, max_retries: int = 5):
        self.base = base
        self.max_retries = max_retries

    def execute(self, func, *args, **kwargs):
        """Execute func with exponential backoff on failure.

        Returns the result of func, or raises after max_retries.
        """
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                if attempt == self.max_retries - 1:
                    raise
                wait = (self.base ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
        raise RateLimitError(f"Failed after {self.max_retries} retries")


class RateLimitError(Exception):
    """Raised when Reddit returns 429 Too Many Requests."""
    pass
