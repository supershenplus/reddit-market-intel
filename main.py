"""Reddit Market Intelligence Pipeline — CLI Entrypoint."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.table import Table

from config import (
    SEED_SUBREDDITS, DEFAULT_LIMIT, DEFAULT_SORT,
    LLM_BATCH_SIZE, LLM_MAX_POSTS_PER_RUN, LLM_RAG_PREFILTER,
)
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
    compute_lienclear_relevance,
)
from analysis.clustering import PainPointClusterer
from analysis.niches import NicheBuilder
from discovery.subreddit_finder import SubredditFinder
from export.report import ReportGenerator
from export.competitor_gaps import CompetitorGapReport
from export.seo_phrases import SEOPhraseReport
from export.digest import DigestWriter
from analysis.cluster_delta import (
    save_snapshot,
    load_snapshot,
    load_snapshot_competitor_counts,
    snapshot_path,
    compute_delta,
    compute_competitor_counts,
    compute_competitor_delta,
    render_delta_report,
)

console = Console()


@click.group()
def cli():
    """Reddit Market Intelligence — find SaaS opportunities from user pain points."""
    pass


def _scrape_one_subreddit(db, scraper, sub, category, limit, sort, comments):
    """Scrape one sub + update its metadata. Returns (new_posts, new_comments)."""
    posts = scraper.fetch_posts(sub, limit=limit, sort=sort)

    new_posts = 0
    new_comments = 0
    for post in posts:
        if db.insert_post(post.to_dict()):
            new_posts += 1
            if comments and post.num_comments > 0:
                post_comments = scraper.fetch_comments(post.reddit_id)
                for comment in post_comments:
                    comment_dict = comment.to_dict()
                    flags = classify_comment(comment)
                    comment_dict.update(flags)
                    db.insert_comment(comment_dict)
                    new_comments += 1

    info = scraper.get_subreddit_info(sub)
    db.upsert_subreddit({
        "name": sub,
        "subscribers": info.get("subscribers", 0),
        "category": category,
        "discovered_from": None,
        "last_scraped": datetime.now(timezone.utc).isoformat(),
        "active": 1,
    })
    return new_posts, new_comments


def _flatten_seed_subreddits():
    """SEED_SUBREDDITS dict → ordered list of (sub, category) tuples, deduped by sub.
    First category-wins on duplicates so a sub stays pinned to its primary vertical."""
    seen = {}
    for category, subs in SEED_SUBREDDITS.items():
        for sub in subs:
            seen.setdefault(sub, category)
    return list(seen.items())


def _is_scraped_within(last_scraped_iso, cutoff_dt):
    """True if last_scraped_iso parses to a datetime >= cutoff_dt.
    Returns False for null, malformed, or legacy 'now' literal strings — those
    are treated as never-scraped so scrape-all re-fetches them."""
    if not last_scraped_iso:
        return False
    try:
        ts = datetime.fromisoformat(last_scraped_iso)
    except (TypeError, ValueError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts >= cutoff_dt


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
        new_posts, new_comments = _scrape_one_subreddit(
            db, scraper, sub, category, limit, sort, comments,
        )
        total_posts += new_posts
        total_comments += new_comments
        console.print(f"  [green]New posts: {new_posts}, comments: {new_comments}[/green]")

    console.print(f"\n[bold green]Done! {total_posts} new posts, {total_comments} comments stored.[/bold green]")
    db.close()


@cli.command("scrape-all")
@click.option(
    "--max-age-days", "-a", default=7, show_default=True, type=int,
    help="Skip subs scraped within this many days (0 = always scrape).",
)
@click.option("--limit", "-l", default=DEFAULT_LIMIT, help="Max posts per subreddit")
@click.option("--sort", default=DEFAULT_SORT, type=click.Choice(["hot", "new", "top"]))
@click.option("--comments/--no-comments", default=True, help="Also fetch comment threads")
def scrape_all(max_age_days, limit, sort, comments):
    """Scrape every configured subreddit, skipping those scraped within --max-age-days."""
    db = Database()
    scraper = get_scraper()

    pairs = _flatten_seed_subreddits()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    to_scrape = []
    skipped = []
    for sub, category in pairs:
        info = db.get_subreddit_info(sub)
        last = info.get("last_scraped") if info else None
        if _is_scraped_within(last, cutoff):
            skipped.append(sub)
        else:
            to_scrape.append((sub, category))

    console.print(
        f"[bold]Scrape-all: {len(to_scrape)} subs to scrape, "
        f"{len(skipped)} skipped (scraped within {max_age_days}d).[/bold]"
    )

    total_posts = 0
    total_comments = 0
    failures = []
    for sub, category in to_scrape:
        console.print(f"\n[bold]Scraping r/{sub} ({category}, {sort}, limit={limit})...[/bold]")
        try:
            new_posts, new_comments = _scrape_one_subreddit(
                db, scraper, sub, category, limit, sort, comments,
            )
        except Exception as e:
            console.print(f"  [red]Error on r/{sub}: {e}[/red]")
            failures.append(sub)
            continue
        total_posts += new_posts
        total_comments += new_comments
        console.print(f"  [green]New posts: {new_posts}, comments: {new_comments}[/green]")

    console.print(
        f"\n[bold green]Done! {total_posts} new posts, {total_comments} comments "
        f"across {len(to_scrape) - len(failures)} subs.[/bold green]"
    )
    if failures:
        console.print(f"[yellow]Failed: {', '.join(failures)}[/yellow]")
    db.close()


@cli.command()
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-analyze all posts (drops pain_points + clusters first)",
)
@click.option(
    "--deep-profile",
    type=click.Choice(["lienclear"]),
    default=None,
    help="Run an optional deep-profile overlay on each classified post "
    "(extracts thesis-specific facets into matched_patterns). "
    "Off by default — the discovery path is thesis-agnostic.",
)
def analyze(force, deep_profile):
    """Run analysis pipeline: classify, validate, score, and cluster pain points."""
    db = Database()
    classifier = PainPointClassifier()
    scorer = OpportunityScorer()

    if force:
        try:
            with db.conn:
                db.conn.execute("DELETE FROM pain_points")
                db.conn.execute("DELETE FROM clusters")
        except Exception as e:
            console.print(f"[red]--force failed clearing tables: {e}[/red]")
            db.close()
            raise
        console.print("[yellow]--force: cleared pain_points + clusters. Re-analyzing all posts.[/yellow]")

    # Step 1: Classify unanalyzed posts
    unanalyzed = db.get_posts_without_pain_points()
    console.print(f"[bold]Analyzing {len(unanalyzed)} unprocessed posts...[/bold]")
    if deep_profile:
        console.print(f"[dim]Deep profile active: {deep_profile}[/dim]")

    matched = 0
    for post in unanalyzed:
        result = classifier.classify(post["title"], post["body"])
        if result:
            try:
                existing_mp = json.loads(result["matched_patterns"])
            except (TypeError, ValueError, json.JSONDecodeError):
                existing_mp = []
            mp_payload = {"intent": existing_mp}
            if deep_profile == "lienclear":
                mp_payload["lienclear"] = compute_lienclear_relevance(
                    post["title"] or "", post["body"] or "", post["subreddit"]
                )
            result["matched_patterns"] = json.dumps(mp_payload)

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
    console.print(
        f"[bold green]Done! Classified {matched} new pain points this run. "
        f"DB now: {len(all_pp)} pain points in {len(clusters)} clusters.[/bold green]"
    )
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
@click.option(
    "--profile",
    type=click.Choice(["default", "lienclear"]),
    default="default",
    help="Report overlay: 'default' (generic SMB) or 'lienclear' (construction lien-waiver SaaS).",
)
def export(top, output, min_score, profile):
    """Export clustered opportunity report as markdown."""
    db = Database()
    generator = ReportGenerator(db, profile=profile if profile != "default" else None)
    report = generator.generate(top_n=top, min_score=min_score)

    Path(output).write_text(report, encoding="utf-8")
    console.print(f"[bold green]Report exported to {output}[/bold green]")
    if profile != "default":
        console.print(f"[dim]Profile: {profile}[/dim]")
    console.print(f"[dim]Open in Claude Code: 'Analyze {output} for market opportunities'[/dim]")
    db.close()


@cli.command("lienclear-competitor-gaps")
@click.option(
    "--output", "-o",
    default="data/lienclear_competitor_gaps.md",
    help="Output markdown path",
)
@click.option(
    "--posts-per-competitor", default=5, show_default=True,
    help="How many top pain-pointed posts to show per competitor",
)
@click.option(
    "--quotes-per-competitor", default=5, show_default=True,
    help="How many negative-quote excerpts to show per competitor",
)
def lienclear_competitor_gaps(output, posts_per_competitor, quotes_per_competitor):
    """Export a per-competitor gap report (W5-7) — markdown to disk."""
    db = Database()
    report = CompetitorGapReport(
        db,
        posts_per_competitor=posts_per_competitor,
        quotes_per_competitor=quotes_per_competitor,
    ).generate()
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(report, encoding="utf-8")
    console.print(f"[bold green]Competitor gap report exported to {output}[/bold green]")
    db.close()


@cli.command("lienclear-seo-phrases")
@click.option(
    "--output", "-o",
    default="data/lienclear_seo_phrases.csv",
    help="Output CSV path",
)
@click.option(
    "--min-relevance", default=0.30, show_default=True,
    help="Minimum lienclear_relevance score for a post to feed the phrase extractor",
)
@click.option(
    "--top", "-n", default=100, show_default=True,
    help="Top N phrases to export, ranked by frequency × avg_relevance",
)
def lienclear_seo_phrases(output, min_relevance, top):
    """Export SEO bigram/trigram candidates from domain-hit posts (W5-8)."""
    db = Database()
    report = SEOPhraseReport(
        db, min_relevance=min_relevance, top_n=top,
    ).generate()
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(report, encoding="utf-8")
    console.print(f"[bold green]SEO phrase report exported to {output}[/bold green]")
    db.close()


@cli.command()
@click.option(
    "--date", "snapshot_date", default=None,
    help="Override snapshot date (YYYY-MM-DD). Default: today.",
)
def snapshot(snapshot_date):
    """Snapshot current clusters table to `data/cluster_snapshots/<date>.json` (W5-11)."""
    db = Database()
    path = save_snapshot(db, snapshot_date)
    console.print(f"[bold green]Cluster snapshot saved to {path}[/bold green]")
    db.close()


@cli.command()
@click.option(
    "--baseline", required=True,
    help="Baseline snapshot date (YYYY-MM-DD) — must exist under data/cluster_snapshots/",
)
@click.option(
    "--output", "-o", default="reports/delta_report.md",
    help="Output markdown path",
)
def delta(baseline, output):
    """Diff current clusters vs a prior snapshot (W5-11). Outputs NEW / GROWING / DEAD / SCORE_CHANGED report."""
    db = Database()
    baseline_path = snapshot_path(baseline)
    if not baseline_path.exists():
        console.print(f"[red]Baseline snapshot not found: {baseline_path}[/red]")
        db.close()
        return
    baseline_clusters = load_snapshot(baseline_path)
    baseline_competitor_counts = load_snapshot_competitor_counts(baseline_path)
    current = db.get_all_clusters()
    current_competitor_counts = compute_competitor_counts(db)
    delta_dict = compute_delta(current, baseline_clusters)
    competitor_delta = compute_competitor_delta(
        current_competitor_counts, baseline_competitor_counts,
    )
    report = render_delta_report(
        delta_dict,
        baseline_date=baseline,
        competitor_delta=competitor_delta,
    )
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(report, encoding="utf-8")
    console.print(f"[bold green]Delta report exported to {output}[/bold green]")
    db.close()


@cli.command()
@click.option("--top", "-n", default=10, show_default=True, help="Number of niches to surface")
@click.option(
    "--output", "-o", default=None,
    help="Output markdown path (default: reports/weekly/<today>.md)",
)
@click.option(
    "--n-niches", default=15, show_default=True,
    help="Niche count for k-means meta-clustering",
)
def digest(top, output, n_niches):
    """Build niches from clusters and emit the weekly markdown digest (Phase 1)."""
    db = Database()
    console.print(f"[bold]Meta-clustering into {n_niches} niches via k-means on cluster centroids...[/bold]")
    builder = NicheBuilder(db, n_niches=n_niches)
    written = builder.rebuild()
    if written == 0:
        console.print(
            "[yellow]Not enough multi-post clusters to form niches. "
            "Run `python main.py scrape` + `analyze` first.[/yellow]"
        )
        db.close()
        return

    writer = DigestWriter(db)
    md = writer.generate(top_n=top)

    if output is None:
        from datetime import date
        output = f"reports/weekly/{date.today().isoformat()}.md"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(md, encoding="utf-8")
    console.print(f"[bold green]Digest exported to {output}[/bold green]")
    console.print(f"[dim]{written} niches written. Open: {output}[/dim]")
    db.close()


def _default_prefilter() -> str:
    """Config LLM_RAG_PREFILTER (bool) maps to a CLI default: True->strict,
    False->off. 'sampled' must be requested explicitly via --prefilter."""
    return "strict" if LLM_RAG_PREFILTER else "off"


@cli.command("llm-export")
@click.option(
    "--batch-size", default=LLM_BATCH_SIZE, show_default=True, type=int,
    help="Posts per batch file. Sized for ~50K input tokens.",
)
@click.option(
    "--max-posts", default=LLM_MAX_POSTS_PER_RUN, show_default=True, type=int,
    help="Hard cap on total posts selected per run.",
)
@click.option(
    "--prefilter", default=None,
    type=click.Choice(["strict", "sampled", "off"]),
    help="RAG pre-filter mode. Default: strict if LLM_RAG_PREFILTER else off.",
)
@click.option(
    "--re-extract", is_flag=True, default=False,
    help="Re-extract posts that already have a current-version facet.",
)
@click.option(
    "--output-root", default=None,
    help="Override the batch output root (default: data/llm_batches/).",
)
def llm_export(batch_size, max_posts, prefilter, re_extract, output_root):
    """Phase 3 — export posts to LLM batch markdown files."""
    from analysis.llm_extractor import select_posts, export_batches

    db = Database()
    prefilter = prefilter or _default_prefilter()
    console.print(
        f"[bold]Selecting posts (prefilter={prefilter}, max={max_posts}, "
        f"re_extract={re_extract})...[/bold]"
    )
    posts = select_posts(
        db, prefilter=prefilter, max_posts=max_posts, re_extract=re_extract,
    )
    if not posts:
        console.print(
            "[yellow]No posts to extract. All current at prompt_version, "
            "or no posts match the pre-filter.[/yellow]"
        )
        db.close()
        return

    output_dir = export_batches(
        posts, batch_size=batch_size,
        output_root=Path(output_root) if output_root else None,
    )
    n_batches = (len(posts) + batch_size - 1) // batch_size
    console.print(
        f"[bold green]Exported {len(posts)} posts in {n_batches} batches.[/bold green]"
    )
    console.print(f"[dim]Output: {output_dir}[/dim]")
    db.close()


@cli.command("llm-import")
@click.argument("batch_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def llm_import(batch_dir):
    """Phase 3 — import facets JSON from a previously-exported batch directory."""
    from analysis.llm_extractor import import_facets

    db = Database()
    try:
        result = import_facets(Path(batch_dir), db)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Import failed: {e}[/red]")
        db.close()
        raise click.exceptions.Exit(code=1)

    console.print(f"[bold green]Imported {result['imported']} facets.[/bold green]")
    for w in result["warnings"]:
        console.print(f"[yellow]warning: {w}[/yellow]")
    for e in result["errors"]:
        console.print(f"[red]error: {e}[/red]")
    db.close()


@cli.command("llm-extract")
@click.option(
    "--batch-size", default=LLM_BATCH_SIZE, show_default=True, type=int,
)
@click.option(
    "--max-posts", default=LLM_MAX_POSTS_PER_RUN, show_default=True, type=int,
)
@click.option(
    "--prefilter", default=None,
    type=click.Choice(["strict", "sampled", "off"]),
)
@click.option("--re-extract", is_flag=True, default=False)
def llm_extract(batch_size, max_posts, prefilter, re_extract):
    """Phase 3 — top-level driver: export batches + print operator handoff.

    Run this, then open a Claude Code session and follow the printed
    instructions. After the session writes facets, run `llm-import`."""
    from analysis.llm_extractor import select_posts, export_batches

    db = Database()
    prefilter = prefilter or _default_prefilter()
    console.print(
        f"[bold]Selecting posts (prefilter={prefilter}, max={max_posts}, "
        f"re_extract={re_extract})...[/bold]"
    )
    posts = select_posts(
        db, prefilter=prefilter, max_posts=max_posts, re_extract=re_extract,
    )
    if not posts:
        console.print(
            "[yellow]No posts to extract. All current at prompt_version, "
            "or no posts match the pre-filter.[/yellow]"
        )
        db.close()
        return

    output_dir = export_batches(posts, batch_size=batch_size)
    n_batches = (len(posts) + batch_size - 1) // batch_size
    console.print(
        f"[bold green]Exported {len(posts)} posts in {n_batches} batches.[/bold green]\n"
    )

    # Operator handoff — copy/pasteable next steps
    console.print("[bold]Next steps:[/bold]")
    console.print(
        f"  1. Open a Claude Code session in this project.\n"
        f"  2. Tell it: [cyan]Process the batches in {output_dir} per the embedded "
        f"schema in each batch_NNN.md. Write the facets array to "
        f"batch_NNN_facets.json next to each batch file.[/cyan]\n"
        f"  3. When done, run: [cyan]python main.py llm-import {output_dir}[/cyan]\n"
    )
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
