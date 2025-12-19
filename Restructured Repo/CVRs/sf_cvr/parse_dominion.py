#!/usr/bin/env python3
"""
Stream-parse Dominion CVR JSON exports.

Handles large CVR files efficiently without loading entire JSON into memory.
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Iterator, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class BallotMark:
    """A single mark on a ballot"""
    candidate_id: int
    rank: int  # 0 for non-RCV, 1-N for RCV
    is_vote: bool
    is_ambiguous: bool


@dataclass
class BallotContest:
    """Contest data from a single ballot"""
    contest_id: int
    marks: List[BallotMark] = field(default_factory=list)
    undervotes: int = 0
    overvotes: int = 0


@dataclass
class Ballot:
    """A complete ballot with metadata"""
    ballot_id: str
    precinct_id: Optional[int] = None
    ballot_type_id: Optional[int] = None
    batch_id: Optional[int] = None
    tabulator_id: Optional[int] = None
    contests: Dict[int, BallotContest] = field(default_factory=dict)


def extract_cvr_files(zip_path: Path, extract_dir: Path) -> Path:
    """
    Extract CVR ZIP to directory.

    Args:
        zip_path: Path to CVR ZIP file
        extract_dir: Directory to extract to

    Returns:
        Path to extraction directory
    """
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Check if already extracted
    manifest_path = extract_dir / "ContestManifest.json"
    if manifest_path.exists():
        print(f"Using cached extraction: {extract_dir}")
        return extract_dir

    print(f"Extracting CVR ZIP to: {extract_dir}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    print(f"Extraction complete: {extract_dir}")
    return extract_dir


def iter_cvr_export_files(extracted_dir: Path) -> Iterator[Path]:
    """
    Iterate over CvrExport_*.json files in order.

    Args:
        extracted_dir: Directory containing extracted CVR files

    Yields:
        Paths to CvrExport_*.json files in sorted order
    """
    cvr_files = sorted(extracted_dir.glob("CvrExport_*.json"),
                      key=lambda p: int(p.stem.split('_')[1]))

    for cvr_file in cvr_files:
        yield cvr_file


def parse_cvr_file(cvr_file: Path) -> Iterator[Ballot]:
    """
    Parse a single CvrExport_*.json file and yield ballots.

    Args:
        cvr_file: Path to CvrExport JSON file

    Yields:
        Ballot objects
    """
    with open(cvr_file, 'r') as f:
        data = json.load(f)

    # Each file has "Sessions" containing ballots
    for session in data.get("Sessions", []):
        # Extract metadata
        tabulator_id = session.get("TabulatorId")
        batch_id = session.get("BatchId")
        record_id = session.get("RecordId", "")

        # Generate unique ballot ID
        ballot_id = f"{tabulator_id}_{batch_id}_{record_id}"

        # Get original ballot data (not modified by adjudication)
        original = session.get("Original", {})
        if not original:
            continue

        precinct_id = original.get("PrecinctPortionId")
        ballot_type_id = original.get("BallotTypeId")

        ballot = Ballot(
            ballot_id=ballot_id,
            precinct_id=precinct_id,
            ballot_type_id=ballot_type_id,
            batch_id=batch_id,
            tabulator_id=tabulator_id
        )

        # Parse contests from all cards
        for card in original.get("Cards", []):
            for contest_data in card.get("Contests", []):
                contest_id = contest_data["Id"]
                undervotes = contest_data.get("Undervotes", 0)
                overvotes = contest_data.get("Overvotes", 0)

                contest = BallotContest(
                    contest_id=contest_id,
                    undervotes=undervotes,
                    overvotes=overvotes
                )

                # Parse marks
                for mark_data in contest_data.get("Marks", []):
                    if mark_data.get("IsVote", False):
                        mark = BallotMark(
                            candidate_id=mark_data["CandidateId"],
                            rank=mark_data.get("Rank", 0),
                            is_vote=True,
                            is_ambiguous=mark_data.get("IsAmbiguous", False)
                        )
                        contest.marks.append(mark)

                ballot.contests[contest_id] = contest

        yield ballot


def iter_all_ballots(extracted_dir: Path) -> Iterator[Ballot]:
    """
    Iterate over all ballots from all CVR export files.

    Args:
        extracted_dir: Directory containing extracted CVR files

    Yields:
        Ballot objects
    """
    cvr_files = list(iter_cvr_export_files(extracted_dir))
    print(f"Processing {len(cvr_files)} CVR export files...")

    ballot_count = 0
    for i, cvr_file in enumerate(cvr_files, 1):
        if i % 100 == 0 or i == len(cvr_files):
            print(f"  Processing file {i}/{len(cvr_files)} ({cvr_file.name})")

        for ballot in parse_cvr_file(cvr_file):
            ballot_count += 1
            yield ballot

    print(f"Total ballots processed: {ballot_count:,}")


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 2:
        print("Usage: parse_dominion.py <extracted_dir>")
        sys.exit(1)

    extracted_dir = Path(sys.argv[1])

    # Test parsing
    ballot_count = 0
    contest_ids = set()

    for ballot in iter_all_ballots(extracted_dir):
        ballot_count += 1
        for contest_id in ballot.contests:
            contest_ids.add(contest_id)

        if ballot_count >= 100:  # Test first 100
            break

    print(f"\nTest results:")
    print(f"  Ballots parsed: {ballot_count}")
    print(f"  Unique contests: {len(contest_ids)}")
    print(f"  Contest IDs: {sorted(contest_ids)}")
