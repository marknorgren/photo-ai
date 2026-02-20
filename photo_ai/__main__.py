"""Entry point: parse args and dispatch subcommands."""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Handle SIGPIPE gracefully (e.g. piping to head)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger("photo_ai")

SUBCOMMANDS = {"scan", "eval", "top", "bottom", "tags", "find", "info", "stats", "report", "export", "publish"}


def _looks_like_path(arg: str) -> bool:
    """Check if an argument looks like a filesystem path rather than a subcommand."""
    return arg.startswith(("/", ".", "~")) or os.path.isdir(arg)


def _register_heif() -> None:
    """Register HEIF/HEIC support if available."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        log.warning("pillow-heif not available — HEIC/HEIF files will be skipped")


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    """Add --provider, --model, --base-url to a subparser."""
    from .providers import PROVIDERS, DEFAULT_PROVIDER
    provider_names = ", ".join(PROVIDERS)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, choices=PROVIDERS.keys(), help=f"Vision model provider ({provider_names})")
    parser.add_argument("--model", default=None, help="Model name (default depends on provider)")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234/v1", help="LM Studio server URL (lmstudio provider only)")


def main() -> None:
    # Auto-prepend 'scan' if first arg is a path
    if len(sys.argv) > 1 and sys.argv[1] not in SUBCOMMANDS and sys.argv[1] not in ("-h", "--help", "-v", "--verbose"):
        if _looks_like_path(sys.argv[1]):
            sys.argv.insert(1, "scan")

    parser = argparse.ArgumentParser(prog="analyze.py", description="Photo analysis CLI — analyze, query, and export photo data")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--db", default="photo_analysis.db", help="SQLite database path (default: photo_analysis.db)")
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Analyze photos in a directory")
    p_scan.add_argument("directory", type=Path, help="Directory of images to analyze")
    _add_provider_args(p_scan)
    p_scan.add_argument("--force", action="store_true", help="Re-analyze already processed images")
    p_scan.add_argument("--max-images", type=int, default=0, help="Limit number of images (0 = all)")
    p_scan.add_argument("--max-dimension", type=int, default=1024, help="Max image dimension for resizing")
    p_scan.add_argument("--dry-run", action="store_true", help="Preview which images would be analyzed")

    # eval
    p_eval = sub.add_parser("eval", help="Run model evaluation against golden dataset")
    p_eval.add_argument("eval_file", type=Path, help="Golden evaluation JSON file")
    _add_provider_args(p_eval)
    p_eval.add_argument("--max-dimension", type=int, default=1024, help="Max image dimension for resizing")

    # top
    p_top = sub.add_parser("top", help="Show top-scoring photos")
    p_top.add_argument("n", nargs="?", type=int, default=10, help="Number of photos (default: 10)")
    p_top.add_argument("--category", help="Filter by category")
    p_top.add_argument("--tag", help="Filter by tag")

    # bottom
    p_bottom = sub.add_parser("bottom", help="Show lowest-scoring photos")
    p_bottom.add_argument("n", nargs="?", type=int, default=10, help="Number of photos (default: 10)")

    # tags
    p_tags = sub.add_parser("tags", help="Show tag frequency")
    p_tags.add_argument("--min", type=int, default=1, dest="min_count", help="Minimum count to show")

    # find
    p_find = sub.add_parser("find", help="Search photos with filters")
    p_find.add_argument("--tag", help="Filter by tag")
    p_find.add_argument("--category", help="Filter by category")
    p_find.add_argument("--location", help="Filter by location (substring match)")
    p_find.add_argument("--score", help="Score filter: '6' (exact), '5+' (>=5), '3-5' (range)")

    # info
    p_info = sub.add_parser("info", help="Show detail for one photo")
    p_info.add_argument("photo", help="Photo filename or path fragment")

    # stats
    sub.add_parser("stats", help="Show database summary")

    # report
    p_report = sub.add_parser("report", help="Generate markdown report to stdout")
    p_report.add_argument("--category", help="Filter by category")

    # export
    p_export = sub.add_parser("export", help="Export data as JSON or CSV")
    p_export.add_argument("--format", choices=["json", "csv"], default="json", dest="fmt", help="Output format (default: json)")

    # publish
    p_publish = sub.add_parser("publish", help="Generate gallery markdown with thumbnails")
    p_publish.add_argument("--top", type=int, default=20, dest="top_n", help="Number of top photos (default: 20)")
    p_publish.add_argument("--all", action="store_true", dest="all_photos", help="Include all photos")
    p_publish.add_argument("--title", default="Photo Gallery", help="Gallery title")
    p_publish.add_argument("--gist", action="store_true", help="Push to GitHub Gist via gh CLI")
    p_publish.add_argument("--public", action="store_true", help="Make gist public (default: secret)")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Commands that need a write-mode DB
    if args.command == "scan":
        _register_heif()
        from .db import init_db, get_analyzed_paths
        from .providers import create_provider
        from .scanner import find_images, process_images, print_scan_summary

        if not args.directory.is_dir():
            print(f"Error: {args.directory} is not a directory", file=sys.stderr)
            sys.exit(1)

        all_images = find_images(args.directory)
        if not all_images:
            print("No images found in", args.directory)
            sys.exit(0)

        conn = init_db(args.db)
        analyzed = get_analyzed_paths(conn) if not args.force else set()
        to_process = [img for img in all_images if str(img.resolve()) not in analyzed]

        if args.max_images > 0:
            to_process = to_process[:args.max_images]

        print(f"Found {len(all_images)} images, {len(to_process)} to analyze")

        if args.dry_run:
            for img in to_process:
                print(f"  {img}")
            conn.close()
            return

        if not to_process:
            print("Nothing to do — all images already analyzed. Use --force to re-analyze.")
            print_scan_summary(conn)
            conn.close()
            return

        _client, model_name, analyze_fn = create_provider(args.provider, model=args.model, base_url=args.base_url)
        print(f"Provider: {args.provider}, Model: {model_name}")
        success, errors = process_images(to_process, analyze_fn=analyze_fn, model=model_name, conn=conn, max_dimension=args.max_dimension)
        print(f"\nDone: {success} analyzed, {errors} errors, {len(all_images) - len(to_process)} skipped (already in db)")
        print_scan_summary(conn)
        conn.close()
        return

    if args.command == "eval":
        _register_heif()
        from .providers import create_provider
        from .eval import run_eval

        if not args.eval_file.exists():
            print(f"Error: {args.eval_file} not found", file=sys.stderr)
            sys.exit(1)
        _client, model_name, analyze_fn = create_provider(args.provider, model=args.model, base_url=args.base_url)
        print(f"Provider: {args.provider}, Model: {model_name}")
        run_eval(args.eval_file, analyze_fn=analyze_fn, model=model_name, max_dimension=args.max_dimension)
        return

    # Commands that need a read-only DB
    if args.command == "publish":
        _register_heif()

    from .db import open_db_readonly
    db_path = args.db
    if not Path(db_path).exists():
        print(f"Error: database '{db_path}' not found. Run 'scan' first.", file=sys.stderr)
        sys.exit(1)

    conn = open_db_readonly(db_path)

    if args.command == "top":
        from .queries import cmd_top
        cmd_top(conn, args.n, category=args.category, tag=args.tag)
    elif args.command == "bottom":
        from .queries import cmd_bottom
        cmd_bottom(conn, args.n)
    elif args.command == "tags":
        from .queries import cmd_tags
        cmd_tags(conn, min_count=args.min_count)
    elif args.command == "find":
        from .queries import cmd_find
        cmd_find(conn, tag=args.tag, category=args.category, location=args.location, score_filter=args.score)
    elif args.command == "info":
        from .queries import cmd_info
        cmd_info(conn, args.photo)
    elif args.command == "stats":
        from .queries import cmd_stats
        cmd_stats(conn)
    elif args.command == "report":
        from .report import cmd_report
        cmd_report(conn, category=args.category)
    elif args.command == "export":
        from .report import cmd_export
        cmd_export(conn, fmt=args.fmt)
    elif args.command == "publish":
        from .publish import cmd_publish
        cmd_publish(conn, top_n=args.top_n, title=args.title, gist=args.gist, public=args.public, all_photos=args.all_photos)

    conn.close()


if __name__ == "__main__":
    main()
