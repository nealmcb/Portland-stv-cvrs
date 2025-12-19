#!/usr/bin/env python3
"""
Generate BLT files and contest statistics from CSV CVRs.
"""

import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple

from .manifests import Manifests, Contest


def extract_contest_from_unified_csv(
    csv_path: Path,
    contest: Contest,
    manifests: Manifests
) -> Tuple[Counter, int]:
    """
    Extract a single contest's data from the unified CSV.

    Returns:
        Tuple of (ranking_counts, num_ballots)
    """
    candidates = manifests.get_contest_candidates(contest.id)
    non_writein_candidates = [c for c in candidates if not c.is_writein]

    # Find column indices for this contest
    with open(csv_path, 'r', encoding='utf-8') as f:
        header_line = f.readline().strip()
        headers = next(csv.reader([header_line]))

    # Map columns for this contest
    # Format: "Contest Name - Candidate(Rank)"
    contest_columns = {}
    for idx, header in enumerate(headers):
        if not header.startswith(contest.description):
            continue

        # Parse header: "MAYOR - DANIEL LURIE(1)"
        parts = header.split(' - ')
        if len(parts) < 2:
            continue

        candidate_part = parts[1]

        # Extract candidate name and rank
        if '(' in candidate_part:
            # RCV: "DANIEL LURIE(1)"
            cand_name = candidate_part[:candidate_part.rfind('(')]
            rank_str = candidate_part[candidate_part.rfind('(')+1:candidate_part.rfind(')')]
            rank = int(rank_str)
        else:
            # Non-RCV: "DANIEL LURIE"
            cand_name = candidate_part
            rank = 0

        # Find candidate by name
        for candidate in non_writein_candidates:
            if candidate.description == cand_name:
                contest_columns[(candidate.id, rank)] = idx
                break

    # Parse ballots
    ranking_counts = Counter()
    metadata_cols = ['CvrNumber', 'TabulatorNum', 'BatchId', 'RecordId', 'BallotType']

    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header
        f.readline()

        reader = csv.reader(f)
        for row in reader:
            if len(row) < len(metadata_cols):
                continue

            # Extract ranking for this contest
            ranking = []

            if contest.is_rcv:
                # RCV: extract by rank
                for rank in range(1, contest.num_of_ranks + 1):
                    for candidate in non_writein_candidates:
                        key = (candidate.id, rank)
                        if key in contest_columns:
                            col_idx = contest_columns[key]
                            if col_idx < len(row) and row[col_idx].strip() == '1':
                                if candidate.id not in ranking:
                                    ranking.append(candidate.id)
                                break
            else:
                # Non-RCV
                for candidate in non_writein_candidates:
                    key = (candidate.id, 0)
                    if key in contest_columns:
                        col_idx = contest_columns[key]
                        if col_idx < len(row) and row[col_idx].strip() == '1':
                            ranking.append(candidate.id)

            # Add to profile
            if ranking:
                ranking_counts[tuple(ranking)] += 1

    num_ballots = sum(ranking_counts.values())
    return ranking_counts, num_ballots


def csv_to_blt(csv_path: Path, blt_path: Path, contest: Contest, manifests: Manifests) -> Tuple[int, int]:
    """
    Convert CSV CVR to BLT format.

    Args:
        csv_path: Path to unified CSV CVR file
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

    # Extract this contest's data from unified CSV
    ranking_counts, _ = extract_contest_from_unified_csv(csv_path, contest, manifests)

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
    csv_path: Path,
    output_dir: Path,
    election_slug: str = None
):
    """
    Generate BLT files and statistics table for all RCV contests.

    Args:
        extracted_dir: Directory with extracted CVR files
        csv_path: Path to unified CSV CVR file
        output_dir: Directory to write BLT files and stats
        election_slug: Optional election identifier (e.g., 'sf_20241105')
    """
    # Load manifests
    print("Loading manifests...")
    manifests = Manifests(extracted_dir)

    rcv_contests = manifests.get_rcv_contests()
    print(f"Found {len(rcv_contests)} RCV contests")

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return

    # Derive election slug from output_dir if not provided
    if election_slug is None:
        election_slug = output_dir.name

    # Get CSV file size
    csv_total_size_kb = csv_path.stat().st_size / 1024
    print(f"Unified CSV size: {csv_total_size_kb:.1f} KB ({csv_total_size_kb/1024:.1f} MB)")

    # Prepare output directories
    blt_dir = output_dir / "ranking_profiles"
    blt_dir.mkdir(parents=True, exist_ok=True)

    # Generate BLT for each contest and collect stats
    stats_data = []

    for contest in rcv_contests:
        print(f"\nProcessing: {contest.description}")

        blt_path = blt_dir / f"{election_slug}_{contest.slug}.blt"

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
            'blt_size_kb': blt_size_kb
        })

        print(f"  Ballots: {num_ballots:,}, Unique rankings: {num_unique:,}")
        print(f"  BLT: {blt_size_kb:.1f} KB")

    # Generate markdown table
    markdown_path = output_dir / "contest_statistics.md"
    generate_markdown_table(stats_data, markdown_path, csv_total_size_kb)

    print(f"\nStatistics saved to: {markdown_path}")
    print(f"BLT files saved to: {blt_dir}/")


def generate_markdown_table(stats_data: List[Dict], output_path: Path, csv_total_size_kb: float):
    """Generate markdown table with contest statistics."""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Contest Statistics - San Francisco Election\n\n")

        # Table header
        f.write("| Contest Name | Winners | Candidates | Ballots | Unique Rankings | BLT Profile (KB) |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")

        # Data rows
        total_ballots = 0
        total_unique = 0
        total_blt_size = 0.0

        for stats in stats_data:
            f.write(f"| {stats['contest']} ")
            f.write(f"| {stats['seats']} ")
            f.write(f"| {stats['candidates']} ")
            f.write(f"| {stats['ballots']:,} ")
            f.write(f"| {stats['unique_rankings']:,} ")
            f.write(f"| {stats['blt_size_kb']:.1f} |\n")

            total_ballots += stats['ballots']
            total_unique += stats['unique_rankings']
            total_blt_size += stats['blt_size_kb']

        # Totals row
        f.write(f"| **TOTAL** | - | - | **{total_ballots:,}** ")
        f.write(f"| **{total_unique:,}** | **{total_blt_size:.1f}** |\n")

        # Summary
        f.write("\n## Summary\n\n")
        f.write(f"- **Total RCV contests:** {len(stats_data)}\n")
        f.write(f"- **Total ballots:** {total_ballots:,}\n")
        f.write(f"- **Total unique rankings:** {total_unique:,}\n")
        f.write(f"- **Unified CSV CVR size:** {csv_total_size_kb:.1f} KB ({csv_total_size_kb/1024:.1f} MB)\n")
        f.write(f"- **Total BLT profile size:** {total_blt_size:.1f} KB ({total_blt_size/1024:.1f} MB)\n")
        reduction_pct = (total_blt_size / csv_total_size_kb * 100) if csv_total_size_kb > 0 else 0
        f.write(f"- **BLT compression ratio:** {reduction_pct:.1f}%\n")
        f.write(f"- **Space savings:** {((csv_total_size_kb - total_blt_size) / csv_total_size_kb * 100):.1f}%\n")


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
