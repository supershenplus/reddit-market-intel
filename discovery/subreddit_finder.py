"""Subreddit discovery — find related subs from sidebar links and crossposts."""

import re

from rich.console import Console

from scraper.base import BaseScraper
from storage.db import Database

console = Console()

# Pattern to find subreddit mentions in sidebar/descriptions
SUBREDDIT_PATTERN = re.compile(r"/?r/([A-Za-z0-9_]+)", re.IGNORECASE)


class SubredditFinder:
    """Discovers related subreddits from sidebar descriptions and crosspost patterns."""

    def __init__(self, scraper: BaseScraper, db: Database):
        self.scraper = scraper
        self.db = db

    def discover_from_sidebar(self, subreddit: str) -> list[str]:
        """Parse a subreddit's sidebar/description for mentions of other subreddits.

        Returns list of discovered subreddit names.
        """
        info = self.scraper.get_subreddit_info(subreddit)
        full_desc = info.get("full_description", "") or ""
        short_desc = info.get("description", "") or ""
        text = f"{full_desc} {short_desc}"

        # Find all r/SubredditName mentions
        matches = SUBREDDIT_PATTERN.findall(text)
        # Deduplicate, case-insensitive, exclude self
        seen = set()
        discovered = []
        for match in matches:
            lower = match.lower()
            if lower not in seen and lower != subreddit.lower():
                seen.add(lower)
                discovered.append(match)

        if discovered:
            console.print(
                f"[green]Discovered {len(discovered)} related subs from r/{subreddit} sidebar[/green]"
            )
            for sub in discovered:
                console.print(f"  - r/{sub}")

        return discovered

    def discover_from_crossposts(self, subreddit: str, limit: int = 50) -> list[str]:
        """Find subreddits that users crosspost to/from.

        Looks at posts in the subreddit and finds crosspost origins.
        """
        # The JSON API includes crosspost_parent_list in post data
        # We check recent posts for crosspost sources
        from scraper.json_scraper import JsonScraper

        # Use JSON scraper directly for this (simpler API)
        scraper = JsonScraper()
        import requests

        url = f"{scraper.BASE_URL}/r/{subreddit}/new.json"
        params = {"limit": limit, "raw_json": 1}

        try:
            scraper.rate_limiter.wait()
            resp = scraper.session.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            console.print(f"[red]Error discovering crossposts: {e}[/red]")
            return []

        crosspost_subs = {}
        children = data.get("data", {}).get("children", [])
        for child in children:
            d = child["data"]
            # Check for crosspost parents
            xposts = d.get("crosspost_parent_list", [])
            for xp in xposts:
                xp_sub = xp.get("subreddit", "")
                if xp_sub.lower() != subreddit.lower():
                    crosspost_subs[xp_sub] = crosspost_subs.get(xp_sub, 0) + 1

        # Sort by frequency
        sorted_subs = sorted(crosspost_subs, key=crosspost_subs.get, reverse=True)
        if sorted_subs:
            console.print(
                f"[green]Found {len(sorted_subs)} crosspost-related subs from r/{subreddit}[/green]"
            )

        return sorted_subs

    def discover_and_save(self, source_subreddit: str, category: str = None):
        """Discover related subs and save them to the database.

        Args:
            source_subreddit: The subreddit to discover from.
            category: Category to assign discovered subs (inherits from source if None).
        """
        # Get source category if not specified
        if not category:
            existing = self.db.get_active_subreddits()
            for sub in existing:
                if sub["name"].lower() == source_subreddit.lower():
                    category = sub.get("category")
                    break

        # Discover from sidebar
        sidebar_subs = self.discover_from_sidebar(source_subreddit)

        # Discover from crossposts
        crosspost_subs = self.discover_from_crossposts(source_subreddit)

        # Merge and deduplicate
        all_discovered = list(set(sidebar_subs + crosspost_subs))

        # Save to DB
        saved = 0
        for sub_name in all_discovered:
            info = self.scraper.get_subreddit_info(sub_name)
            subscribers = info.get("subscribers", 0)

            # Skip very small or very large subs (likely noise)
            if subscribers < 1000 or subscribers > 10_000_000:
                continue

            self.db.upsert_subreddit({
                "name": sub_name,
                "subscribers": subscribers,
                "category": category,
                "discovered_from": source_subreddit,
                "last_scraped": None,
                "active": 1,
            })
            saved += 1

        console.print(f"[green]Saved {saved} new subreddits to database[/green]")
        return all_discovered
