"""Abstract base class for Reddit scrapers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RedditPost:
    """Standardized post representation across scraper backends."""
    reddit_id: str
    subreddit: str
    title: str
    body: str
    author: str
    url: str
    score: int
    num_comments: int
    created_utc: float

    def to_dict(self) -> dict:
        return {
            "reddit_id": self.reddit_id,
            "subreddit": self.subreddit,
            "title": self.title,
            "body": self.body,
            "author": self.author,
            "url": self.url,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
        }


@dataclass
class RedditComment:
    """Standardized comment representation."""
    reddit_id: str
    post_reddit_id: str
    parent_reddit_id: str | None
    author: str
    body: str
    score: int
    created_utc: float

    def to_dict(self) -> dict:
        return {
            "reddit_id": self.reddit_id,
            "post_reddit_id": self.post_reddit_id,
            "parent_reddit_id": self.parent_reddit_id,
            "author": self.author,
            "body": self.body,
            "score": self.score,
            "created_utc": self.created_utc,
            "is_me_too": 0,
            "links_product": 0,
            "product_negative": 0,
        }


class BaseScraper(ABC):
    """Abstract interface for Reddit scrapers."""

    @abstractmethod
    def fetch_posts(self, subreddit: str, limit: int = 100, sort: str = "hot") -> list[RedditPost]:
        """Fetch posts from a subreddit.

        Args:
            subreddit: Name without r/ prefix.
            limit: Max posts to return.
            sort: One of 'hot', 'new', 'top'.

        Returns:
            List of RedditPost objects.
        """
        ...

    @abstractmethod
    def fetch_comments(self, post_reddit_id: str, limit: int = 200) -> list[RedditComment]:
        """Fetch comments for a given post.

        Args:
            post_reddit_id: The Reddit ID of the post (e.g., 't3_abc123' or just 'abc123').
            limit: Max comments to fetch.

        Returns:
            List of RedditComment objects.
        """
        ...

    @abstractmethod
    def get_subreddit_info(self, subreddit: str) -> dict:
        """Get metadata about a subreddit (subscribers, description, etc.)."""
        ...
