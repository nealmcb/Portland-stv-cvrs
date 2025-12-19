#!/usr/bin/env python3
"""
Export contests to CSV format (Dominion-style CVR).

Generates a single CSV file with all contests, one row per ballot.
"""

import csv
from pathlib import Path
from typing import Dict, List, Tuple

from .manifests import Manifests, Contest, Candidate
from .parse_dominion import Ballot, iter_all_ballots


def build_column_structure(contests: List[Contest], manifests: Manifests):
    """
    Build column headers and mapping for all contests.

    Returns:
        Tuple of (headers, column_map)
        - headers: List of column header strings
        - column_map: Dict mapping (contest_id, candidate_id, rank) -> column_index
    """
    headers = ["CvrNumber", "TabulatorNum", "BatchId", "RecordId", "BallotType"]
    column_map = {}
    col_idx = len(headers)

    for contest in contests:
        candidates = manifests.get_contest_candidates(contest.id)
        non_writein = [c for c in candidates if not c.is_writein]

        if contest.is_rcv:
            # RCV: Candidate(1), Candidate(2), etc.
            for rank in range(1, contest.num_of_ranks + 1):
                for candidate in non_writein:
                    header = f"{contest.description} - {candidate.description}({rank})"
                    headers.append(header)
                    column_map[(contest.id, candidate.id, rank)] = col_idx
                    col_idx += 1
        else:
            # Non-RCV: Just candidate name
            for candidate in non_writein:
                header = f"{contest.description} - {candidate.description}"
                headers.append(header)
                column_map[(contest.id, candidate.id, 0)] = col_idx  # rank=0 for non-RCV
                col_idx += 1

    return headers, column_map


def export_all_contests_single_csv(
    extracted_dir: Path,
    output_path: Path,
    rcv_only: bool = False
):
    """
    Export all contests to a single CSV file.

    Args:
        extracted_dir: Directory with extracted CVR files
        output_path: Path to output CSV file
        rcv_only: If True, only export RCV contests
    """
    # Load manifests
    print("Loading manifests...")
    manifests = Manifests(extracted_dir)

    # Get contests to export
    if rcv_only:
        contests = manifests.get_rcv_contests()
        print(f"Found {len(contests)} ranked-choice voting contests")
    else:
        contests = manifests.get_all_contests()
        print(f"Found {len(contests)} total contests")

    # Sort contests by ID for determinism
    contests = sorted(contests, key=lambda c: c.id)

    # Build column structure
    print("Building column headers...")
    headers, column_map = build_column_structure(contests, manifests)
    print(f"Total columns: {len(headers)}")

    # Load all ballots
    print("\nLoading all ballots...")
    ballots = list(iter_all_ballots(extracted_dir))
    print(f"Loaded {len(ballots):,} ballots")

    # Write CSV
    print(f"\nWriting CSV to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Single header row
        writer.writerow(headers)

        # Data rows
        for cvr_number, ballot in enumerate(ballots, 1):
            # Initialize row with metadata and empty marks
            row = [
                str(cvr_number),
                str(ballot.tabulator_id) if ballot.tabulator_id else '',
                str(ballot.batch_id) if ballot.batch_id else '',
                str(ballot.ballot_id),
                str(ballot.ballot_type_id) if ballot.ballot_type_id else ''
            ]

            # Add empty marks for all columns
            num_mark_cols = len(headers) - 5  # Subtract metadata columns
            row.extend([''] * num_mark_cols)

            # Fill in marks for contests on this ballot
            for contest_id, ballot_contest in ballot.contests.items():
                for mark in ballot_contest.marks:
                    if not mark.is_vote:
                        continue

                    # Look up column index
                    rank = mark.rank if mark.rank > 0 else 0  # 0 for non-RCV
                    key = (contest_id, mark.candidate_id, rank)

                    if key in column_map:
                        col_idx = column_map[key]
                        row[col_idx] = "1"

            writer.writerow(row)

            if cvr_number % 10000 == 0:
                print(f"  Wrote {cvr_number:,} ballots...")

    print(f"\nComplete! Wrote {len(ballots):,} ballots to {output_path}")

    # Print contest summary
    print("\nContests included:")
    for contest in contests:
        candidates = manifests.get_contest_candidates(contest.id)
        num_candidates = len([c for c in candidates if not c.is_writein])
        if contest.is_rcv:
            print(f"  {contest.description}: {num_candidates} candidates, {contest.num_of_ranks} ranks")
        else:
            print(f"  {contest.description}: {num_candidates} candidates")


def export_all_contests(
    extracted_dir: Path,
    output_dir: Path,
    rcv_only: bool = False
):
    """
    Export all contests to CSV format.

    This now creates a single unified CSV file instead of per-contest files.

    Args:
        extracted_dir: Directory with extracted CVR files
        output_dir: Directory to write CSV file
        rcv_only: If True, only export RCV contests
    """
    csv_path = output_dir / "cvr_all_contests.csv"
    export_all_contests_single_csv(extracted_dir, csv_path, rcv_only=rcv_only)

    return csv_path


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 3:
        print("Usage: export_csv.py <extracted_dir> <output_file> [--rcv-only]")
        sys.exit(1)

    extracted_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    rcv_only = "--rcv-only" in sys.argv

    export_all_contests_single_csv(extracted_dir, output_path, rcv_only=rcv_only)
