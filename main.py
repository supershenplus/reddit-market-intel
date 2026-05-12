"""Reddit Market Intelligence Pipeline — CLI Entrypoint."""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.table import Table

from config import SEED_SUBREDDITS, DEFAULT_LIMIT, DEFAULT_SORT
from storage.db import Database
from scraper.praw_scraper import get_scraper
from scraper.comments import classify_comment
from analysis.classifier import PainPointClassifier
from analysis.validators import compute_validation_score
from analysis.scorer import OpportunityScorer
from analysis.market_signals import (
    compute_monetization_score,
    compute_solution_simplicity,
    compute_market_size_score,
)
from analysis.clustering import PainPointClusterer
from discovery.subreddit_finder import SubredditFinder
from export.report import ReportGenerator

console = Console()


@click.group()
def cli():
    """Reddit Market Intelligence — find SaaS opportunities from user pain points."""
    pass


@cli.command()
@click.option("--subreddit", "-s", help="Specific subreddit to scrape")
@click.option("--category", "-c", help="Scrape all subs in a category (from config)")
@click.option("--limit", "-l", default=DEFAULT_LIMIT, help="Max posts per subreddit")
@click.option("--sort", default=DEFAULT_SORT, type=click.Choice(["hot", "new", "top"]))
@click.option("--comments/--no-comments", default=True, help="Also fetch comment threads")
def scrape(subreddit, category, limit, sort, comments):
    """Scrape posts (and optionally comments) from Reddit."""
    db = Database()
    scraper = get_scraper()

    # Determine which subreddits to scrape
    targets = []
    if subreddit:
        targets = [subreddit]
    elif category:
        if category in SEED_SUBREDDITS:
            targets = SEED_SUBREDDITS[category]
        else:
            # Check DB for category
            db_subs = db.get_active_subreddits(category=category)
            targets = [s["name"] for s in db_subs]
        if not targets:
            console.print(f"[red]No subreddits found for category: {category}[/red]")
            return
    else:
        console.print("[red]Specify --subreddit or --category[/red]")
        return

    total_posts = 0
    total_comments = 0

    for sub in targets:
        console.print(f"\n[bold]Scraping r/{sub} ({sort}, limit={limit})...[/bold]")
        posts = scraper.fetch_posts(sub, limit=limit, sort=sort)

        new_posts = 0
        for post in posts:
            if db.insert_post(post.to_dict()):
                new_posts += 1

                # Fetch comments for new posts
                if comments and post.num_comments > 0:
                    post_comments = scraper.fetch_comments(post.reddit_id)
                    for comment in post_comments:
                        comment_dict = comment.to_dict()
                        # Classify comment validation signals
                        flags = classify_comment(comment)
                        comment_dict.update(flags)
                        db.insert_comment(comment_dict)
                        total_comments += 1

        total_posts += new_posts
        console.print(f"  [green]New posts: {new_posts}[/green] (skipped {len(posts) - new_posts} duplicates)")

        # Update subreddit metadata
        info = scraper.get_subreddit_info(sub)
        db.upsert_subreddit({
            "name": sub,
            "subscribers": info.get("subscribers", 0),
            "category": category,
            "discovered_from": None,
            "last_scraped": "now",
            "active": 1,
        })

    console.print(f"\n[bold green]Done! {total_posts} new posts, {total_comments} comments stored.[/bold green]")
    db.close()


@cli.command()
def analyze():
    """Run analysis pipeline: classify, validate, score, and cluster pain points."""
    db = Database()
    classifier = PainPointClassifier()
    scorer = OpportunityScorer()

    # Step 1: Classify unanalyzed posts
    unanalyzed = db.get_posts_without_pain_points()
    console.print(f"[bold]Analyzing {len(unanalyzed)} unprocessed posts...[/bold]")

    matched = 0
    for post in unanalyzed:
        result = classifier.classify(post["title"], post["body"])
        if result:
            # Get validation score from comments
            comments_raw = db.get_comments_for_post(post["reddit_id"])
            # Convert to RedditComment-like objects for validator
            from scraper.base import RedditComment
            comments = [
                RedditComment(
                    reddit_id=c["reddit_id"],
                    post_reddit_id=c["post_reddit_id"],
                    parent_reddit_id=c["parent_reddit_id"],
                    author=c["author"],
                    body=c["body"],
                    score=c["score"],
                    created_utc=c["created_utc"],
                )
                for c in comments_raw
            ]

            validation = compute_validation_score(comments)
            recency = scorer.compute_recency_weight(post["created_utc"])

            # Market signals
            sub_info = db.get_subreddit_info(post["subreddit"])
            subscribers = sub_info.get("subscribers", 0) if sub_info else 0
            mono = compute_monetization_score(post["title"] or "", post["body"] or "", post["subreddit"])
            simplicity = compute_solution_simplicity(post["title"] or "", post["body"] or "")
            mkt_size = compute_market_size_score(subscribers, cross_sub_count=1)

            # Compute opportunity score
            opp_score = scorer.score(
                reddit_score=post["score"],
                sentiment_intensity=result["sentiment_intensity"],
                validation_score=validation,
                cross_sub_count=1,  # updated during clustering
                intent_category=result["intent_category"],
                created_utc=post["created_utc"],
                monetization_score=mono,
                solution_simplicity=simplicity,
                market_size_score=mkt_size,
            )

            pain_point = {
                "post_id": post["id"],
                "matched_patterns": result["matched_patterns"],
                "intent_category": result["intent_category"],
                "opportunity_score": opp_score,
                "sentiment_intensity": result["sentiment_intensity"],
                "validation_score": validation,
                "recency_weight": recency,
                "cross_sub_count": 1,
                "cluster_id": None,
                "monetization_score": mono,
                "solution_simplicity": simplicity,
                "market_size_score": mkt_size,
            }
            db.insert_pain_point(pain_point)
            matched += 1

    console.print(f"[green]Classified {matched} pain points from {len(unanalyzed)} posts[/green]")

    # Step 2: Cluster
    console.print("[bold]Clustering pain points...[/bold]")
    clusterer = PainPointClusterer(db)
    clusterer.cluster()

    # Step 3: Re-score with cross-sub data
    console.print("[bold]Re-scoring with cross-subreddit data...[/bold]")
    all_pp = db.get_all_pain_points()
    for pp in all_pp:
        new_score = scorer.score(
            reddit_score=pp["reddit_score"] or 0,
            sentiment_intensity=pp["sentiment_intensity"] or 0,
            validation_score=pp["validation_score"] or 0,
            cross_sub_count=pp["cross_sub_count"] or 1,
            intent_category=pp["intent_category"] or "feature_request",
            created_utc=pp["created_utc"] or 0,
            monetization_score=pp.get("monetization_score") or 0.5,
            solution_simplicity=pp.get("solution_simplicity") or 0.5,
            market_size_score=pp.get("market_size_score") or 0.3,
        )
        db.update_pain_point_score(pp["id"], new_score)

    clusters = db.get_all_clusters()
    console.print(f"[bold green]Done! {matched} pain points in {len(clusters)} clusters.[/bold green]")
    db.close()


@cli.command()
@click.option("--from", "from_sub", required=True, help="Source subreddit to discover from")
@click.option("--category", "-c", help="Category to assign discovered subs")
def discover(from_sub, category):
    """Discover related subreddits from a source subreddit's sidebar and crossposts."""
    db = Database()
    scraper = get_scraper()
    finder = SubredditFinder(scraper, db)
    finder.discover_and_save(from_sub, category=category)
    db.close()


@cli.command()
@click.option("--top", "-n", default=20, help="Number of top opportunities to export")
@click.option("--output", "-o", default="report.md", help="Output file path")
@click.option("--min-score", default=0.0, help="Minimum opportunity score threshold")
def export(top, output, min_score):
    """Export clustered opportunity report as markdown."""
    db = Database()
    generator = ReportGenerator(db)
    report = generator.generate(top_n=top, min_score=min_score)

    Path(output).write_text(report, encoding="utf-8")
    console.print(f"[bold green]Report exported to {output}[/bold green]")
    console.print(f"[dim]Open in Claude Code: 'Analyze {output} for market opportunities'[/dim]")
    db.close()


@cli.command()
def status():
    """Show database statistics and top clusters."""
    db = Database()
    stats = db.get_stats()

    table = Table(title="Database Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    table.add_row("Posts", str(stats["posts"]))
    table.add_row("Comments", str(stats["comments"]))
    table.add_row("Pain Points", str(stats["pain_points"]))
    table.add_row("Clusters", str(stats["clusters"]))
    table.add_row("Subreddits", str(stats["subreddits"]))
    table.add_row("Top Score", f"{stats['top_score']:.3f}")
    console.print(table)

    # Show top clusters
    clusters = db.get_all_clusters()[:5]
    if clusters:
        console.print("\n[bold]Top Opportunities:[/bold]")
        for i, c in enumerate(clusters, 1):
            import json
            subs = json.loads(c["subreddits"]) if c["subreddits"] else []
            trending = " 🔥" if c["trending"] else ""
            console.print(
                f"  {i}. [bold]{c['label']}[/bold] "
                f"(score: {c['avg_opportunity_score']:.2f}, "
                f"posts: {c['post_count']}, "
                f"subs: {', '.join(subs[:3])}){trending}"
            )

    db.close()


if __name__ == "__main__":
    cli()
