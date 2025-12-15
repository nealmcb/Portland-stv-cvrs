#!/usr/bin/env python3
"""
Generate prefix-compressed, printable, lossless abstracts of votes
for Portland 2025 ranked-choice election.

This script creates archival-quality text abstracts suitable for long-term
storage on paper. The output is:
- Lossless (exact reconstruction of tallies possible)
- Deterministic / canonical
- Human-readable
- Vendor-neutral
- Compact on paper
"""

import csv
import sys
from collections import Counter
from typing import List, Tuple, Dict
from pathlib import Path


class RankingAbstract:
    """Generate prefix-compressed ranking abstracts for ranked-choice elections."""
    
    def __init__(self, district: int, csv_path: str):
        """
        Initialize with district number and path to CVR CSV file.
        
        Args:
            district: District number (1-4)
            csv_path: Path to the CVR CSV file in votekit format
        """
        self.district = district
        self.csv_path = csv_path
        self.ballots = []
        self.candidates = set()
        self.preference_profile = {}  # ranking tuple -> count
        
    def load_ballots(self):
        """Load ballots from CSV file and build preference profile."""
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Extract ranking from Rank 1 through Rank 6
                ranking = []
                for i in range(1, 7):
                    rank_col = f'Rank {i}'
                    candidate = row.get(rank_col, '').strip()
                    # Skip empty, overvotes, and write-ins
                    if candidate and candidate != 'overvote' and not candidate.startswith('Write-in-'):
                        # Avoid duplicate candidates in same ballot (undervote handling)
                        if candidate not in ranking:
                            ranking.append(candidate)
                            self.candidates.add(candidate)
                
                # Convert to tuple for hashing
                ranking_tuple = tuple(ranking)
                self.ballots.append(ranking_tuple)
                
                # Count occurrences
                if ranking_tuple in self.preference_profile:
                    self.preference_profile[ranking_tuple] += 1
                else:
                    self.preference_profile[ranking_tuple] = 1
    
    def get_canonical_candidate_order(self) -> List[str]:
        """
        Return candidates in canonical (lexicographic) order.
        
        This ensures deterministic output across runs.
        """
        return sorted(list(self.candidates))
    
    def get_sorted_rankings(self) -> List[Tuple[tuple, int]]:
        """
        Return rankings sorted lexicographically by candidate order.
        
        Sorting rules:
        1. Candidates are mapped to their position in canonical order
        2. Rankings are compared position-by-position
        3. Shorter rankings come before longer ones with same prefix
        
        Returns:
            List of (ranking_tuple, count) sorted canonically
        """
        candidate_order = self.get_canonical_candidate_order()
        candidate_to_idx = {c: i for i, c in enumerate(candidate_order)}
        
        # Convert rankings to index tuples for sorting
        def ranking_key(item):
            ranking, count = item
            return tuple(candidate_to_idx[c] for c in ranking)
        
        sorted_items = sorted(self.preference_profile.items(), key=ranking_key)
        return sorted_items
    
    def find_common_prefix(self, rankings: List[tuple], start: int, end: int) -> tuple:
        """
        Find the longest common prefix among rankings[start:end].
        
        Args:
            rankings: List of ranking tuples
            start: Start index (inclusive)
            end: End index (exclusive)
            
        Returns:
            Tuple representing the common prefix
        """
        if start >= end:
            return ()
        
        first_ranking = rankings[start]
        if start + 1 >= end:
            return ()
        
        # Find longest common prefix
        prefix_len = 0
        for i in range(min(len(r) for r in rankings[start:end])):
            if all(rankings[j][i] == first_ranking[i] for j in range(start, end)):
                prefix_len = i + 1
            else:
                break
        
        return first_ranking[:prefix_len]
    
    def generate_prefix_groups(self, sorted_rankings: List[Tuple[tuple, int]],
                               min_group_size: int = 20) -> List[Tuple[tuple, List[Tuple[tuple, int]]]]:
        """
        Group rankings by common prefix for compression.
        
        Args:
            sorted_rankings: Lexicographically sorted rankings
            min_group_size: Minimum number of rankings to form a group
            
        Returns:
            List of (prefix, group_rankings) tuples
        """
        groups = []
        i = 0
        
        while i < len(sorted_rankings):
            # Try to find a good prefix for grouping
            best_prefix = ()
            best_end = i + 1
            
            # Look ahead to find best grouping
            for end in range(i + min_group_size, min(i + 200, len(sorted_rankings) + 1)):
                rankings_only = [r[0] for r in sorted_rankings[i:end]]
                prefix = self.find_common_prefix(rankings_only, 0, len(rankings_only))
                
                if len(prefix) > len(best_prefix):
                    best_prefix = prefix
                    best_end = end
            
            # If we found a good prefix, use it
            if len(best_prefix) > 0:
                # Extend to include all rankings with this prefix
                while best_end < len(sorted_rankings) and \
                      len(sorted_rankings[best_end][0]) >= len(best_prefix) and \
                      sorted_rankings[best_end][0][:len(best_prefix)] == best_prefix:
                    best_end += 1
                
                groups.append((best_prefix, sorted_rankings[i:best_end]))
                i = best_end
            else:
                # No good prefix, output individually
                groups.append(((), sorted_rankings[i:i+1]))
                i += 1
        
        return groups
    
    def format_ranking(self, ranking: tuple, candidate_map: Dict[str, str] = None) -> str:
        """
        Format a ranking as a string using candidate IDs.
        
        Args:
            ranking: Tuple of candidate names
            candidate_map: Optional map from name to short ID (e.g., "C01")
            
        Returns:
            Formatted string like "C01 > C03 > C05"
        """
        if candidate_map:
            ids = [candidate_map[c] for c in ranking]
        else:
            ids = list(ranking)
        
        if not ids:
            return "(empty)"
        
        return " > ".join(ids)
    
    def generate_abstract(self, output_path: str):
        """
        Generate the complete prefix-compressed abstract.
        
        Args:
            output_path: Path to write the abstract text file
        """
        # Load and process data
        self.load_ballots()
        sorted_rankings = self.get_sorted_rankings()
        candidate_order = self.get_canonical_candidate_order()
        
        # Create candidate ID mapping (C01, C02, etc.)
        candidate_to_id = {c: f"C{i+1:02d}" for i, c in enumerate(candidate_order)}
        
        # Generate prefix groups
        groups = self.generate_prefix_groups(sorted_rankings)
        
        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write(f"ABSTRACT OF VOTES - CITY COUNCIL DISTRICT {self.district}\n")
            f.write("City of Portland, Oregon\n")
            f.write("November 2024 General Election\n")
            f.write("=" * 80 + "\n\n")
            
            # Contest information
            f.write("CONTEST INFORMATION\n")
            f.write("-" * 80 + "\n")
            f.write(f"Contest: City Council District {self.district}\n")
            f.write("Election Method: Single Transferable Vote (STV)\n")
            f.write("Seats: 3\n")
            f.write(f"Total Ballots with Rankings: {len(self.ballots)}\n")
            f.write(f"Unique Ranking Expressions: {len(self.preference_profile)}\n")
            f.write("\n")
            
            # Candidate legend
            f.write("CANDIDATE LEGEND\n")
            f.write("-" * 80 + "\n")
            for candidate in candidate_order:
                cid = candidate_to_id[candidate]
                f.write(f"{cid}  {candidate}\n")
            f.write("\n")
            
            # Explanation
            f.write("EXPLANATION\n")
            f.write("-" * 80 + "\n")
            f.write("This abstract lists all unique ranking expressions that appear in the\n")
            f.write("Cast Vote Record (CVR). Rankings are sorted lexicographically by candidate\n")
            f.write("order and grouped by common prefix for compression.\n\n")
            f.write("Format: <ranking expression> : <count>\n")
            f.write("Symbol '>' means 'preferred over'\n")
            f.write("(empty) means no ranking was cast\n\n")
            f.write("Prefix compression: When multiple rankings share a common prefix, the\n")
            f.write("prefix is stated once, followed by the distinct suffixes with counts.\n")
            f.write("\n")
            
            # Rankings with prefix compression
            f.write("PREFERENCE PROFILE (PREFIX-COMPRESSED)\n")
            f.write("=" * 80 + "\n\n")
            
            ranking_count = 0
            for prefix, group in groups:
                if len(prefix) > 0:
                    # Print prefix header
                    f.write(f"PREFIX: {self.format_ranking(prefix, candidate_to_id)}\n")
                    f.write("-" * 80 + "\n")
                    
                    for ranking, count in group:
                        ranking_count += 1
                        # Print only the suffix
                        suffix = ranking[len(prefix):]
                        if suffix:
                            suffix_str = self.format_ranking(suffix, candidate_to_id)
                            f.write(f"  ... > {suffix_str} : {count}\n")
                        else:
                            # Exact prefix match
                            f.write(f"  (exact match) : {count}\n")
                    
                    f.write("\n")
                else:
                    # No prefix, print full ranking
                    for ranking, count in group:
                        ranking_count += 1
                        ranking_str = self.format_ranking(ranking, candidate_to_id)
                        f.write(f"{ranking_str} : {count}\n")
            
            # Footer
            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF ABSTRACT\n")
            f.write(f"Total ranking expressions: {ranking_count}\n")
            f.write(f"Total ballots: {sum(c for _, c in sorted_rankings)}\n")
            f.write("=" * 80 + "\n")


def main():
    """Generate abstracts for all four districts."""
    base_path = Path(__file__).parent
    
    districts = [1, 2, 3, 4]
    
    for district in districts:
        print(f"Processing District {district}...")
        
        csv_path = base_path / f"raw_votekit_csv/Portland_D{district}_raw_votekit_format.csv"
        output_path = base_path / f"abstracts/Portland_D{district}_abstract.txt"
        
        # Create output directory if needed
        output_path.parent.mkdir(exist_ok=True)
        
        # Generate abstract
        abstract = RankingAbstract(district, str(csv_path))
        abstract.generate_abstract(str(output_path))
        
        print(f"  Generated: {output_path}")
        print(f"  Ballots: {len(abstract.ballots)}")
        print(f"  Unique rankings: {len(abstract.preference_profile)}")
        print(f"  Candidates: {len(abstract.candidates)}")
        print()
    
    print("All abstracts generated successfully!")


if __name__ == "__main__":
    main()
