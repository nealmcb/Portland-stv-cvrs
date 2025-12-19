#!/usr/bin/env python3
"""
Export contests to CSV format (Dominion-style CVR).

Generates CSV files with one row per ballot, columns for each candidate/rank combination.
"""

import csv
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

from .manifests import Manifests, Contest, Candidate
from .parse_dominion import Ballot, iter_all_ballots


def export_contest_csv(
    contest: Contest,
    manifests: Manifests,
    ballots: List[Ballot],
    output_path: Path
):
    """
    Export a single contest to CSV format (Dominion-style).

    Args:
        contest: Contest to export
        manifests: Manifest data (for candidate lookups)
        ballots: List of all ballots
        output_path: Path to write CSV file
    """
    candidates = manifests.get_contest_candidates(contest.id)
    non_writein_candidates = [c for c in candidates if not c.is_writein]

    # Build metadata columns
    metadata_cols = ["CvrNumber", "TabulatorNum", "BatchId", "RecordId", "BallotType"]

    # Build candidate column headers
    # For RCV, we need multiple columns per candidate (one per rank)
    if contest.is_rcv:
        candidate_cols = []
        for rank in range(1, contest.num_of_ranks + 1):
            for candidate in non_writein_candidates:
                candidate_cols.append(candidate.description)
    else:
        candidate_cols = [c.description for c in non_writein_candidates]

    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Row 1: Contest name header (spanning candidate columns)
        row1 = [''] * len(metadata_cols)  # Empty for metadata columns
        for _ in candidate_cols:
            row1.append(contest.description)
        writer.writerow(row1)

        # Row 2: Candidate names
        row2 = metadata_cols + candidate_cols
        writer.writerow(row2)

        # Data rows
        ballot_count = 0
        cvr_number = 1

        for ballot in ballots:
            # Build metadata
            row = [
                str(cvr_number),
                str(ballot.tabulator_id) if ballot.tabulator_id else '',
                str(ballot.batch_id) if ballot.batch_id else '',
                str(ballot.ballot_id),
                str(ballot.ballot_type_id) if ballot.ballot_type_id else ''
            ]

            # Check if contest appears on this ballot
            if contest.id in ballot.contests:
                ballot_contest = ballot.contests[contest.id]

                if contest.is_rcv:
                    # RCV: fill in marks by rank and candidate
                    for rank in range(1, contest.num_of_ranks + 1):
                        for candidate in non_writein_candidates:
                            # Check if this candidate was marked at this rank
                            marked = False
                            for mark in ballot_contest.marks:
                                if mark.candidate_id == candidate.id and mark.rank == rank and mark.is_vote:
                                    marked = True
                                    break

                            row.append("1" if marked else "0")
                else:
                    # Non-RCV: fill in marks by candidate
                    for candidate in non_writein_candidates:
                        marked = False
                        for mark in ballot_contest.marks:
                            if mark.candidate_id == candidate.id and mark.is_vote:
                                marked = True
                                break

                        row.append("1" if marked else "0")
            else:
                # Contest not on this ballot - add empty marks
                num_marks = len(non_writein_candidates) * (contest.num_of_ranks if contest.is_rcv else 1)
                for _ in range(num_marks):
                    row.append("")

            writer.writerow(row)
            ballot_count += 1
            cvr_number += 1

    print(f"  Wrote {ballot_count:,} ballots to {output_path.name}")
    return ballot_count


def export_all_contests(
    extracted_dir: Path,
    output_dir: Path,
    rcv_only: bool = False
):
    """
    Export all contests to CSV format.

    Args:
        extracted_dir: Directory with extracted CVR files
        output_dir: Directory to write CSV files
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

    # Load all ballots into memory
    # (This is necessary since we need to iterate per-contest)
    print("\nLoading all ballots...")
    ballots = list(iter_all_ballots(extracted_dir))
    print(f"Loaded {len(ballots):,} ballots")

    # Export each contest
    print(f"\nExporting contests to: {output_dir}")
    csv_dir = output_dir / "csv_cvrs"
    csv_dir.mkdir(parents=True, exist_ok=True)

    for contest in contests:
        print(f"\nExporting: {contest.description}")
        print(f"  ID: {contest.id}, Slug: {contest.slug}")
        if contest.is_rcv:
            print(f"  Type: RCV ({contest.num_of_ranks} ranks)")
        else:
            print(f"  Type: Plurality")

        candidates = manifests.get_contest_candidates(contest.id)
        print(f"  Candidates: {len(candidates)}")

        output_path = csv_dir / f"{contest.slug}.csv"
        export_contest_csv(contest, manifests, ballots, output_path)


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 3:
        print("Usage: export_csv.py <extracted_dir> <output_dir> [--rcv-only]")
        sys.exit(1)

    extracted_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    rcv_only = "--rcv-only" in sys.argv

    export_all_contests(extracted_dir, output_dir, rcv_only=rcv_only)
