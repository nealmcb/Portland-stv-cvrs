#!/usr/bin/env python3
"""
SF CVR Processing Pipeline CLI

Usage:
    python -m sf_cvr.cli all 20241105 --cvr-url <url>
    python -m sf_cvr.cli fetch 20241105 --cvr-url <url>
    python -m sf_cvr.cli export 20241105
    python -m sf_cvr.cli stats 20241105
"""

import argparse
import sys
from pathlib import Path

from .fetch import fetch_cvr_zip
from .parse_dominion import extract_cvr_files
from .export_csv import export_all_contests
from .stats import generate_contest_statistics


def main():
    parser = argparse.ArgumentParser(
        description="SF CVR Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process entire pipeline
  python -m sf_cvr.cli all 20241105 --cvr-url https://...CVR_Export.zip

  # Step by step
  python -m sf_cvr.cli fetch 20241105 --cvr-url https://...CVR_Export.zip
  python -m sf_cvr.cli export 20241105
  python -m sf_cvr.cli stats 20241105
        """
    )

    parser.add_argument(
        "command",
        choices=["all", "fetch", "export", "stats"],
        help="Command to run"
    )

    parser.add_argument(
        "election_id",
        help="Election date in YYYYMMDD format (e.g., 20241105)"
    )

    parser.add_argument(
        "--cvr-url",
        help="Direct URL to CVR ZIP file (required for fetch)"
    )

    parser.add_argument(
        "--rcv-only",
        action="store_true",
        help="Only process ranked-choice voting contests"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: CVRs/sf_{election_id})"
    )

    args = parser.parse_args()

    # Set default output directory
    if args.output_dir is None:
        args.output_dir = Path(f"CVRs/sf_{args.election_id}")

    print(f"SF CVR Processing Pipeline")
    print(f"Election: {args.election_id}")
    print(f"Output: {args.output_dir}")
    print()

    try:
        if args.command in ["all", "fetch"]:
            run_fetch(args)

        if args.command in ["all", "export"]:
            run_export(args)

        if args.command in ["all", "stats"]:
            run_stats(args)

        print("\n" + "="*80)
        print("Pipeline complete!")
        print(f"Results: {args.output_dir}")
        print("="*80)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def run_fetch(args):
    """Fetch and extract CVR ZIP"""
    print("="*80)
    print("STEP 1: Fetch CVR ZIP")
    print("="*80)

    if args.cvr_url is None:
        print("Error: --cvr-url is required for fetch step", file=sys.stderr)
        sys.exit(1)

    # Download CVR ZIP
    cache_dir = args.output_dir / "cache"
    zip_path = fetch_cvr_zip(args.election_id, args.cvr_url, cache_dir)

    # Extract CVR files
    extracted_dir = args.output_dir / "extracted"
    extract_cvr_files(zip_path, extracted_dir)

    print(f"\nExtracted files: {extracted_dir}")
    print()


def run_export(args):
    """Export contests to CSV"""
    print("="*80)
    print("STEP 2: Export Contests to CSV")
    print("="*80)

    extracted_dir = args.output_dir / "extracted"
    if not extracted_dir.exists():
        print(f"Error: Extracted directory not found: {extracted_dir}", file=sys.stderr)
        print("Run 'fetch' step first.", file=sys.stderr)
        sys.exit(1)

    export_all_contests(
        extracted_dir,
        args.output_dir,
        rcv_only=args.rcv_only
    )

    csv_dir = args.output_dir / "csv_cvrs"
    print(f"\nCSV files: {csv_dir}")
    print()


def run_stats(args):
    """Generate BLT files and statistics"""
    print("="*80)
    print("STEP 3: Generate BLT and Statistics")
    print("="*80)

    extracted_dir = args.output_dir / "extracted"
    csv_dir = args.output_dir / "csv_cvrs"

    if not extracted_dir.exists():
        print(f"Error: Extracted directory not found: {extracted_dir}", file=sys.stderr)
        print("Run 'fetch' step first.", file=sys.stderr)
        sys.exit(1)

    if not csv_dir.exists():
        print(f"Error: CSV directory not found: {csv_dir}", file=sys.stderr)
        print("Run 'export' step first.", file=sys.stderr)
        sys.exit(1)

    generate_contest_statistics(
        extracted_dir,
        csv_dir,
        args.output_dir
    )

    blt_dir = args.output_dir / "blt_profiles"
    stats_file = args.output_dir / "contest_statistics.md"

    print(f"\nBLT files: {blt_dir}")
    print(f"Statistics: {stats_file}")
    print()


if __name__ == "__main__":
    main()
