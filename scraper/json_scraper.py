"""Reddit JSON API scraper — no authentication required."""

import requests
from rich.console import Console

from config import JSON_API_DELAY, JSON_API_JITTER, REDDIT_USER_AGENT, COMMENT_DEPTH
from scraper.base import BaseScraper, RedditPost, RedditComment
from scraper.rate_limiter import RateLimiter, BackoffHandler, RateLimitError

console = Console()


class JsonScraper(BaseScraper):
    """Scrapes Reddit via public JSON endpoints (append .json to URLs)."""

    BASE_URL = "https://www.reddit.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": REDDIT_USER_AGENT})
        self.rate_limiter = RateLimiter(
            requests_per_second=1.0 / JSON_API_DELAY,
            jitter=JSON_API_JITTER,
        )
        self.backoff = BackoffHandler()

    def _get(self, url: str, params: dict = None) -> dict:
        """Make a rate-limited GET request with backoff."""
        self.rate_limiter.wait()

        def _request():
            # (connect, read) timeout — prevents indefinite hangs when Reddit
            # stalls a socket (backoff never fires without this).
            resp = self.session.get(url, params=params, timeout=(5, 30))
            if resp.status_code == 429:
                raise RateLimitError(f"429 from {url}")
            resp.raise_for_status()
            return resp.json()

        return self.backoff.execute(_request)

    def fetch_posts(self, subreddit: str, limit: int = 100, sort: str = "hot") -> list[RedditPost]:
        """Fetch posts using Reddit JSON API with pagination."""
        posts = []
        after = None
        remaining = limit

        while remaining > 0:
            batch_size = min(remaining, 100)  # Reddit caps at 100 per page
            url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
            params = {"limit": batch_size, "raw_json": 1}
            if after:
                params["after"] = after

            try:
                data = self._get(url, params)
            except Exception as e:
                console.print(f"[red]Error fetching r/{subreddit}: {e}[/red]")
                break

            children = data.get("data", {}).get("children", [])
            if not children:
                break

            for child in children:
                d = child["data"]
                posts.append(RedditPost(
                    reddit_id=d["name"],
                    subreddit=d["subreddit"],
                    title=d.get("title", ""),
                    body=d.get("selftext", ""),
                    author=d.get("author", "[deleted]"),
                    url=f"https://www.reddit.com{d.get('permalink', '')}",
                    score=d.get("score", 0),
                    num_comments=d.get("num_comments", 0),
                    created_utc=d.get("created_utc", 0),
                ))

            after = data.get("data", {}).get("after")
            if not after:
                break
            remaining -= len(children)

        console.print(f"[green]Fetched {len(posts)} posts from r/{subreddit}[/green]")
        return posts

    def fetch_comments(self, post_reddit_id: str, limit: int = 200) -> list[RedditComment]:
        """Fetch comment tree for a post."""
        # Strip t3_ prefix if present
        post_id = post_reddit_id.replace("t3_", "")
        url = f"{self.BASE_URL}/comments/{post_id}.json"
        params = {"limit": limit, "depth": COMMENT_DEPTH, "raw_json": 1}

        try:
            data = self._get(url, params)
        except Exception as e:
            console.print(f"[red]Error fetching comments for {post_reddit_id}: {e}[/red]")
            return []

        comments = []
        # data[1] contains the comment listing
        if len(data) > 1:
            self._parse_comment_tree(data[1], post_reddit_id, comments)

        return comments

    def _parse_comment_tree(self, listing: dict, post_reddit_id: str, results: list):
        """Recursively parse comment tree from JSON response."""
        children = listing.get("data", {}).get("children", [])
        for child in children:
            if child["kind"] != "t1":
                continue
            d = child["data"]
            parent = d.get("parent_id")
            # If parent is the post itself, set to None (top-level)
            if parent and parent.startswith("t3_"):
                parent = None

            results.append(RedditComment(
                reddit_id=d["name"],
                post_reddit_id=post_reddit_id,
                parent_reddit_id=parent,
                author=d.get("author", "[deleted]"),
                body=d.get("body", ""),
                score=d.get("score", 0),
                created_utc=d.get("created_utc", 0),
            ))

            # Recurse into replies
            replies = d.get("replies")
            if replies and isinstance(replies, dict):
                self._parse_comment_tree(replies, post_reddit_id, results)

    def get_subreddit_info(self, subreddit: str) -> dict:
        """Fetch subreddit metadata."""
        url = f"{self.BASE_URL}/r/{subreddit}/about.json"
        try:
            data = self._get(url)
            d = data.get("data", {})
            return {
                "name": d.get("display_name", subreddit),
                "subscribers": d.get("subscribers", 0),
                "description": d.get("public_description", ""),
                "full_description": d.get("description", ""),
            }
        except Exception as e:
            console.print(f"[red]Error fetching info for r/{subreddit}: {e}[/red]")
            return {"name": subreddit, "subscribers": 0, "description": "", "full_description": ""}
