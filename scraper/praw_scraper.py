"""PRAW-based Reddit scraper — requires OAuth credentials."""

import praw
from rich.console import Console

from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    COMMENT_DEPTH,
)
from scraper.base import BaseScraper, RedditPost, RedditComment

console = Console()


class PrawScraper(BaseScraper):
    """Scrapes Reddit via PRAW (Python Reddit API Wrapper).

    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars.
    Higher rate limits than JSON API (600 req/10min).
    """

    def __init__(self):
        if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
            raise ValueError(
                "PRAW requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET. "
                "Set them as environment variables or use JsonScraper as fallback."
            )
        self.reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )

    def fetch_posts(self, subreddit: str, limit: int = 100, sort: str = "hot") -> list[RedditPost]:
        """Fetch posts via PRAW."""
        sub = self.reddit.subreddit(subreddit)
        sort_methods = {
            "hot": sub.hot,
            "new": sub.new,
            "top": sub.top,
        }
        fetcher = sort_methods.get(sort, sub.hot)
        posts = []

        try:
            for submission in fetcher(limit=limit):
                posts.append(RedditPost(
                    reddit_id=submission.fullname,
                    subreddit=submission.subreddit.display_name,
                    title=submission.title,
                    body=submission.selftext,
                    author=str(submission.author) if submission.author else "[deleted]",
                    url=f"https://www.reddit.com{submission.permalink}",
                    score=submission.score,
                    num_comments=submission.num_comments,
                    created_utc=submission.created_utc,
                ))
        except Exception as e:
            console.print(f"[red]PRAW error fetching r/{subreddit}: {e}[/red]")

        console.print(f"[green]Fetched {len(posts)} posts from r/{subreddit} (PRAW)[/green]")
        return posts

    def fetch_comments(self, post_reddit_id: str, limit: int = 200) -> list[RedditComment]:
        """Fetch comments via PRAW with 'more comments' expansion."""
        post_id = post_reddit_id.replace("t3_", "")
        comments = []

        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=COMMENT_DEPTH)

            for comment in submission.comments.list()[:limit]:
                parent_id = comment.parent_id
                if parent_id.startswith("t3_"):
                    parent_id = None

                comments.append(RedditComment(
                    reddit_id=comment.fullname,
                    post_reddit_id=post_reddit_id,
                    parent_reddit_id=parent_id,
                    author=str(comment.author) if comment.author else "[deleted]",
                    body=comment.body,
                    score=comment.score,
                    created_utc=comment.created_utc,
                ))
        except Exception as e:
            console.print(f"[red]PRAW error fetching comments for {post_reddit_id}: {e}[/red]")

        return comments

    def get_subreddit_info(self, subreddit: str) -> dict:
        """Fetch subreddit metadata via PRAW."""
        try:
            sub = self.reddit.subreddit(subreddit)
            return {
                "name": sub.display_name,
                "subscribers": sub.subscribers,
                "description": sub.public_description,
                "full_description": sub.description,
            }
        except Exception as e:
            console.print(f"[red]PRAW error fetching info for r/{subreddit}: {e}[/red]")
            return {"name": subreddit, "subscribers": 0, "description": "", "full_description": ""}


def get_scraper() -> BaseScraper:
    """Factory: returns PRAW scraper if credentials available, else JSON fallback."""
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        try:
            console.print("[cyan]Using PRAW scraper (OAuth)[/cyan]")
            return PrawScraper()
        except Exception:
            pass

    console.print("[yellow]No PRAW credentials — using JSON API fallback[/yellow]")
    from scraper.json_scraper import JsonScraper
    return JsonScraper()
