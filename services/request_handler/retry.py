import asyncio
from abc import ABC, abstractmethod


class BackoffStrategy(ABC): # pragma: no cover, interface
    @abstractmethod
    def compute_delay_seconds(self, attempt: int) -> float:
        pass


class ExponentialBackoff(BackoffStrategy):
    def __init__(self, base_seconds: float = 2.0):
        self.base_seconds = base_seconds

    def compute_delay_seconds(self, attempt: int) -> float:
        if attempt <= 0:
            return 0.0
        return float(self.base_seconds ** attempt)


class RetryPolicy(ABC): # pragma: no cover, interface
    @abstractmethod
    def should_retry(self, attempt: int, max_retries: int) -> bool:
        pass

    @abstractmethod
    async def wait_before_retry(self, attempt: int) -> None:
        pass


class DefaultRetryPolicy(RetryPolicy):
    """
    Preserves legacy behavior: retries up to max_retries and waits base^attempt seconds.
    """

    def __init__(self, backoff: BackoffStrategy):
        self.backoff = backoff

    def should_retry(self, attempt: int, max_retries: int) -> bool:
        return attempt <= max_retries

    async def wait_before_retry(self, attempt: int) -> None:
        delay = self.backoff.compute_delay_seconds(attempt)
        await asyncio.sleep(delay)

