#!/usr/bin/env python3
"""
Generate BLT files and contest statistics from CSV CVRs.
"""

import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple

from .manifests import Manifests, Contest


def csv_to_blt(csv_path: Path, blt_path: Path, contest: Contest, manifests: Manifests) -> Tuple[int, int]:
    """
    Convert CSV CVR to BLT format.

    Args:
        csv_path: Path to CSV CVR file
        blt_path: Path to output BLT file
        contest: Contest metadata
        manifests: Manifest data

    Returns:
        Tuple of (num_ballots, num_unique_rankings)
    """
    candidates = manifests.get_contest_candidates(contest.id)
    non_writein_candidates = [c for c in candidates if not c.is_writein]

    # Build candidate ID mapping (sorted by ID for determinism)
    candidate_map = {c.id: idx + 1 for idx, c in enumerate(sorted(non_writein_candidates, key=lambda x: x.id))}
    candidate_names = {idx + 1: c.description for idx, c in enumerate(sorted(non_writein_candidates, key=lambda x: x.id))}

    # Parse CSV and build preference profiles
    # Note: CSV has 2 header rows (contest name, candidate names)
    # Candidate names repeat (once per rank), so we can't use DictReader
    ranking_counts = Counter()

    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip first header row (contest names)
        f.readline()

        # Read second header row (candidate names)
        header_line = f.readline().strip()
        headers = next(csv.reader([header_line]))

        # Find metadata column indices
        metadata_cols = ['CvrNumber', 'TabulatorNum', 'BatchId', 'RecordId', 'BallotType']
        data_start_idx = len(metadata_cols)

        # Parse data rows
        reader = csv.reader(f)
        for row in reader:
            if len(row) < data_start_idx:
                continue  # Skip empty rows

            # Extract ranking from this ballot
            ranking = []

            if contest.is_rcv:
                # RCV: candidates repeat for each rank
                candidates_per_rank = len(non_writein_candidates)

                for rank in range(1, contest.num_of_ranks + 1):
                    start_idx = data_start_idx + (rank - 1) * candidates_per_rank
                    end_idx = start_idx + candidates_per_rank

                    # Find marked candidate at this rank
                    for idx in range(candidates_per_rank):
                        col_idx = start_idx + idx
                        if col_idx < len(row) and row[col_idx].strip() == '1':
                            candidate = non_writein_candidates[idx]
                            if candidate.id not in ranking:
                                ranking.append(candidate.id)
                            break
            else:
                # Non-RCV: one column per candidate
                for idx, candidate in enumerate(non_writein_candidates):
                    col_idx = data_start_idx + idx
                    if col_idx < len(row) and row[col_idx].strip() == '1':
                        ranking.append(candidate.id)

            # Add to profile
            if ranking:
                ranking_counts[tuple(ranking)] += 1

    # Write BLT file
    blt_path.parent.mkdir(parents=True, exist_ok=True)

    with open(blt_path, 'w', encoding='utf-8') as f:
        # Header: num_candidates num_seats
        num_seats = contest.vote_for
        f.write(f"{len(non_writein_candidates)} {num_seats}\n")

        # Ballot lines: count cand1 cand2 ... 0
        for ranking, count in sorted(ranking_counts.items(), key=lambda x: x[1], reverse=True):
            ballot_line = str(count)
            for candidate_id in ranking:
                ballot_line += f" {candidate_map[candidate_id]}"
            ballot_line += " 0\n"
            f.write(ballot_line)

        # End marker
        f.write("0\n")

        # Candidate names
        for idx in range(1, len(non_writein_candidates) + 1):
            f.write(f'"{candidate_names[idx]}"\n')

        # Election title
        f.write(f'"{contest.description}"\n')

    num_ballots = sum(ranking_counts.values())
    num_unique = len(ranking_counts)

    return num_ballots, num_unique


def generate_contest_statistics(
    extracted_dir: Path,
    csv_dir: Path,
    output_dir: Path
):
    """
    Generate BLT files and statistics table for all RCV contests.

    Args:
        extracted_dir: Directory with extracted CVR files
        csv_dir: Directory with CSV CVR files
        output_dir: Directory to write BLT files and stats
    """
    # Load manifests
    print("Loading manifests...")
    manifests = Manifests(extracted_dir)

    rcv_contests = manifests.get_rcv_contests()
    print(f"Found {len(rcv_contests)} RCV contests")

    # Prepare output directories
    blt_dir = output_dir / "blt_profiles"
    blt_dir.mkdir(parents=True, exist_ok=True)

    # Generate BLT for each contest and collect stats
    stats_data = []

    for contest in rcv_contests:
        print(f"\nProcessing: {contest.description}")

        csv_path = csv_dir / f"{contest.slug}.csv"
        if not csv_path.exists():
            print(f"  Warning: CSV not found: {csv_path}")
            continue

        blt_path = blt_dir / f"{contest.slug}.blt"

        # Get CSV file size
        csv_size_kb = csv_path.stat().st_size / 1024

        # Generate BLT
        num_ballots, num_unique = csv_to_blt(csv_path, blt_path, contest, manifests)

        # Get BLT file size
        blt_size_kb = blt_path.stat().st_size / 1024

        # Get candidate count
        candidates = manifests.get_contest_candidates(contest.id)
        num_candidates = len([c for c in candidates if not c.is_writein])

        stats_data.append({
            'contest': contest.description,
            'seats': contest.vote_for,
            'candidates': num_candidates,
            'ballots': num_ballots,
            'unique_rankings': num_unique,
            'csv_size_kb': csv_size_kb,
            'blt_size_kb': blt_size_kb
        })

        print(f"  Ballots: {num_ballots:,}, Unique rankings: {num_unique:,}")
        print(f"  CSV: {csv_size_kb:.1f} KB, BLT: {blt_size_kb:.1f} KB")
        print(f"  Reduction: {(blt_size_kb/csv_size_kb)*100:.1f}%")

    # Generate markdown table
    markdown_path = output_dir / "contest_statistics.md"
    generate_markdown_table(stats_data, markdown_path)

    print(f"\nStatistics saved to: {markdown_path}")
    print(f"BLT files saved to: {blt_dir}/")


def generate_markdown_table(stats_data: List[Dict], output_path: Path):
    """Generate markdown table with contest statistics."""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Contest Statistics - San Francisco Election\n\n")

        # Table header
        f.write("| Contest Name | Winners | Candidates | Ballots | Unique Rankings | CSV CVR (KB) | BLT Profile (KB) | Reduction % |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")

        # Data rows
        total_ballots = 0
        total_unique = 0
        total_csv_size = 0.0
        total_blt_size = 0.0

        for stats in stats_data:
            reduction_pct = (stats['blt_size_kb'] / stats['csv_size_kb'] * 100) if stats['csv_size_kb'] > 0 else 0

            f.write(f"| {stats['contest']} ")
            f.write(f"| {stats['seats']} ")
            f.write(f"| {stats['candidates']} ")
            f.write(f"| {stats['ballots']:,} ")
            f.write(f"| {stats['unique_rankings']:,} ")
            f.write(f"| {stats['csv_size_kb']:.1f} ")
            f.write(f"| {stats['blt_size_kb']:.1f} ")
            f.write(f"| {reduction_pct:.1f}% |\n")

            total_ballots += stats['ballots']
            total_unique += stats['unique_rankings']
            total_csv_size += stats['csv_size_kb']
            total_blt_size += stats['blt_size_kb']

        # Totals row
        total_reduction = (total_blt_size / total_csv_size * 100) if total_csv_size > 0 else 0
        f.write(f"| **TOTAL** | - | - | **{total_ballots:,}** ")
        f.write(f"| **{total_unique:,}** | **{total_csv_size:.1f}** ")
        f.write(f"| **{total_blt_size:.1f}** | **{total_reduction:.1f}%** |\n")

        # Summary
        f.write("\n## Summary\n\n")
        f.write(f"- **Total contests:** {len(stats_data)}\n")
        f.write(f"- **Total ballots:** {total_ballots:,}\n")
        f.write(f"- **Total unique rankings:** {total_unique:,}\n")
        f.write(f"- **Total CSV CVR size:** {total_csv_size:.1f} KB ({total_csv_size/1024:.1f} MB)\n")
        f.write(f"- **Total BLT profile size:** {total_blt_size:.1f} KB ({total_blt_size/1024:.1f} MB)\n")
        f.write(f"- **Compression ratio:** {total_reduction:.1f}%\n")
        f.write(f"- **Space savings:** {((total_csv_size - total_blt_size) / total_csv_size * 100):.1f}%\n")


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 4:
        print("Usage: stats.py <extracted_dir> <csv_dir> <output_dir>")
        sys.exit(1)

    extracted_dir = Path(sys.argv[1])
    csv_dir = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])

    generate_contest_statistics(extracted_dir, csv_dir, output_dir)
