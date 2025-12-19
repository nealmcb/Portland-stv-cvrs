#!/usr/bin/env python3
"""
Parse Dominion manifest files (Contest, Candidate, etc.).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Contest:
    """Contest metadata from ContestManifest.json"""
    id: int
    description: str
    external_id: str
    district_id: int
    vote_for: int
    num_of_ranks: int
    disabled: bool

    @property
    def is_rcv(self) -> bool:
        """Check if this is a ranked-choice voting contest"""
        return self.num_of_ranks > 0

    @property
    def slug(self) -> str:
        """Generate filename-safe slug"""
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', self.description.lower())
        slug = slug.strip('_')
        return f"contest_{self.id}_{slug}"


@dataclass
class Candidate:
    """Candidate metadata from CandidateManifest.json"""
    id: int
    description: str
    external_id: str
    contest_id: int
    type: str  # "Regular" or "WriteIn"
    disabled: bool

    @property
    def is_writein(self) -> bool:
        return self.type == "WriteIn"


class Manifests:
    """Container for all manifest data"""

    def __init__(self, extracted_dir: Path):
        """
        Load manifests from extracted CVR directory.

        Args:
            extracted_dir: Directory containing extracted JSON files
        """
        self.extracted_dir = Path(extracted_dir)

        # Load manifests
        self.contests: Dict[int, Contest] = self._load_contests()
        self.candidates: Dict[int, Candidate] = self._load_candidates()

        # Build candidate lookup by contest
        self.candidates_by_contest: Dict[int, List[Candidate]] = {}
        for candidate in self.candidates.values():
            contest_id = candidate.contest_id
            if contest_id not in self.candidates_by_contest:
                self.candidates_by_contest[contest_id] = []
            self.candidates_by_contest[contest_id].append(candidate)

        # Sort candidates by ID within each contest for determinism
        for contest_id in self.candidates_by_contest:
            self.candidates_by_contest[contest_id].sort(key=lambda c: c.id)

    def _load_contests(self) -> Dict[int, Contest]:
        """Load ContestManifest.json"""
        manifest_path = self.extracted_dir / "ContestManifest.json"
        with open(manifest_path) as f:
            data = json.load(f)

        contests = {}
        for item in data["List"]:
            contest = Contest(
                id=item["Id"],
                description=item["Description"],
                external_id=item["ExternalId"],
                district_id=item["DistrictId"],
                vote_for=item["VoteFor"],
                num_of_ranks=item["NumOfRanks"],
                disabled=item["Disabled"] != 0
            )
            contests[contest.id] = contest

        return contests

    def _load_candidates(self) -> Dict[int, Candidate]:
        """Load CandidateManifest.json"""
        manifest_path = self.extracted_dir / "CandidateManifest.json"
        with open(manifest_path) as f:
            data = json.load(f)

        candidates = {}
        for item in data["List"]:
            candidate = Candidate(
                id=item["Id"],
                description=item["Description"],
                external_id=item["ExternalId"],
                contest_id=item["ContestId"],
                type=item["Type"],
                disabled=item["Disabled"] != 0
            )
            candidates[candidate.id] = candidate

        return candidates

    def get_rcv_contests(self) -> List[Contest]:
        """Get all ranked-choice voting contests"""
        return [c for c in self.contests.values() if c.is_rcv and not c.disabled]

    def get_all_contests(self) -> List[Contest]:
        """Get all contests"""
        return [c for c in self.contests.values() if not c.disabled]

    def get_contest_candidates(self, contest_id: int) -> List[Candidate]:
        """Get all candidates for a contest"""
        return self.candidates_by_contest.get(contest_id, [])


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 2:
        print("Usage: manifests.py <extracted_dir>")
        sys.exit(1)

    extracted_dir = Path(sys.argv[1])
    manifests = Manifests(extracted_dir)

    print(f"Loaded {len(manifests.contests)} contests")
    print(f"Loaded {len(manifests.candidates)} candidates")

    print("\nRanked-Choice Voting Contests:")
    for contest in manifests.get_rcv_contests():
        candidates = manifests.get_contest_candidates(contest.id)
        print(f"  {contest.id}: {contest.description}")
        print(f"    Ranks: {contest.num_of_ranks}, Candidates: {len(candidates)}")
        print(f"    Slug: {contest.slug}")
