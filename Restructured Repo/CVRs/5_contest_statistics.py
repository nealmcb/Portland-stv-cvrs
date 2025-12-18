#!/usr/bin/env python3
"""
Generate a comprehensive statistics table for all contests.

This script analyzes contest data and displays a table with:
- Contest name
- Number of winners (seats)
- Number of candidates
- Number of ballots
- Number of unique rankings
- Size in KB of CVR file (one line per ballot)
- Size in KB of ranking profile BLT file (counts per unique ranking)
"""

import csv
import os
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple


class ContestStatistics:
    """Analyzes and displays contest statistics."""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.raw_csv_dir = self.base_dir / "raw_votekit_csv"
        self.abstracts_dir = self.base_dir / "abstracts"
        self.profiles_dir = self.base_dir / "ranking_profiles"

        # Create profiles directory if it doesn't exist
        self.profiles_dir.mkdir(exist_ok=True)

        # Portland contests configuration
        self.contests = [
            ("Portland District 1", 1),
            ("Portland District 2", 2),
            ("Portland District 3", 3),
            ("Portland District 4", 4),
        ]
        self.num_seats = 3  # All Portland districts elect 3 council members

    def get_cvr_stats(self, district_num: int) -> Tuple[int, int, int]:
        """
        Get statistics from CVR file.

        Returns:
            Tuple of (num_ballots, num_candidates, file_size_kb)
        """
        cvr_file = self.raw_csv_dir / f"Portland_D{district_num}_raw_votekit_format.csv"

        if not cvr_file.exists():
            print(f"Warning: CVR file not found: {cvr_file}")
            return 0, 0, 0

        # Get file size in KB
        file_size_kb = cvr_file.stat().st_size / 1024

        # Read CSV to count ballots and candidates
        with open(cvr_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ballots = list(reader)

            num_ballots = len(ballots)

            # Collect all unique candidates
            candidates = set()
            for ballot in ballots:
                for rank_col in ['Rank 1', 'Rank 2', 'Rank 3', 'Rank 4', 'Rank 5', 'Rank 6']:
                    candidate = ballot.get(rank_col, '').strip()
                    if candidate and candidate != 'overvote' and not candidate.startswith('Write-in'):
                        candidates.add(candidate)

            num_candidates = len(candidates)

        return num_ballots, num_candidates, file_size_kb

    def get_unique_rankings_from_abstract(self, district_num: int) -> int:
        """
        Count unique rankings from abstract file.

        Returns:
            Number of unique ranking expressions
        """
        abstract_file = self.abstracts_dir / f"Portland_D{district_num}_abstract.txt"

        if not abstract_file.exists():
            print(f"Warning: Abstract file not found: {abstract_file}")
            return 0

        # Parse abstract file to count unique rankings
        with open(abstract_file, 'r', encoding='utf-8') as f:
            content = f.read()

            # Look for the unique ranking count in the header
            # Format: "Unique Ranking Expressions: 18895"
            for line in content.split('\n'):
                if 'Unique Ranking Expressions:' in line:
                    count_str = line.split(':')[1].strip().replace(',', '')
                    return int(count_str)

        return 0

    def generate_ranking_profile_csv(self, district_num: int) -> Tuple[int, float]:
        """
        Generate ranking profile CSV file (unique rankings with counts).

        Returns:
            Tuple of (num_unique_rankings, file_size_kb)
        """
        cvr_file = self.raw_csv_dir / f"Portland_D{district_num}_raw_votekit_format.csv"
        profile_file = self.profiles_dir / f"Portland_D{district_num}_ranking_profile.csv"

        if not cvr_file.exists():
            return 0, 0.0

        # Build preference profile
        ranking_counts = Counter()

        with open(cvr_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for ballot in reader:
                # Extract ranking
                ranking = []
                for rank_col in ['Rank 1', 'Rank 2', 'Rank 3', 'Rank 4', 'Rank 5', 'Rank 6']:
                    candidate = ballot.get(rank_col, '').strip()
                    if candidate and candidate != 'overvote' and not candidate.startswith('Write-in'):
                        # Remove duplicates in the same ballot
                        if candidate not in ranking:
                            ranking.append(candidate)

                # Convert to tuple for hashing
                if ranking:
                    ranking_counts[tuple(ranking)] += 1

        # Write profile to CSV
        with open(profile_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Ranking', 'Count'])

            for ranking, count in sorted(ranking_counts.items(), key=lambda x: x[1], reverse=True):
                ranking_str = ' > '.join(ranking)
                writer.writerow([ranking_str, count])

        # Get file size
        file_size_kb = profile_file.stat().st_size / 1024
        num_unique = len(ranking_counts)

        return num_unique, file_size_kb

    def generate_ranking_profile_blt(self, district_num: int) -> Tuple[int, float]:
        """
        Generate ranking profile BLT file (unique rankings with counts in BLT format).

        BLT format is:
        - Line 1: num_candidates num_seats
        - Lines 2-N: count candidate1 candidate2 ... 0 (candidates numbered 1-N)
        - After ballots: 0
        - Candidate names in quotes
        - Election title in quotes

        Returns:
            Tuple of (num_unique_rankings, file_size_kb)
        """
        cvr_file = self.raw_csv_dir / f"Portland_D{district_num}_raw_votekit_format.csv"
        profile_file = self.profiles_dir / f"Portland_D{district_num}_ranking_profile.blt"

        if not cvr_file.exists():
            return 0, 0.0

        # Build preference profile and candidate list
        ranking_counts = Counter()
        all_candidates = set()

        with open(cvr_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for ballot in reader:
                # Extract ranking
                ranking = []
                for rank_col in ['Rank 1', 'Rank 2', 'Rank 3', 'Rank 4', 'Rank 5', 'Rank 6']:
                    candidate = ballot.get(rank_col, '').strip()
                    if candidate and candidate != 'overvote' and not candidate.startswith('Write-in'):
                        # Remove duplicates in the same ballot
                        if candidate not in ranking:
                            ranking.append(candidate)
                            all_candidates.add(candidate)

                # Convert to tuple for hashing
                if ranking:
                    ranking_counts[tuple(ranking)] += 1

        # Create sorted candidate list (alphabetical for consistency)
        candidates = sorted(all_candidates)
        candidate_to_num = {name: idx + 1 for idx, name in enumerate(candidates)}

        # Write BLT file
        with open(profile_file, 'w', encoding='utf-8') as f:
            # Header line: num_candidates num_seats
            f.write(f"{len(candidates)} {self.num_seats}\n")

            # Ballot lines: count candidate1 candidate2 ... 0
            for ranking, count in sorted(ranking_counts.items(), key=lambda x: x[1], reverse=True):
                ballot_line = str(count)
                for candidate in ranking:
                    ballot_line += f" {candidate_to_num[candidate]}"
                ballot_line += " 0\n"
                f.write(ballot_line)

            # End of ballots marker
            f.write("0\n")

            # Candidate names (in order)
            for candidate in candidates:
                f.write(f'"{candidate}"\n')

            # Election title
            f.write(f'"Portland District {district_num}"\n')

        # Get file size
        file_size_kb = profile_file.stat().st_size / 1024
        num_unique = len(ranking_counts)

        return num_unique, file_size_kb

    def format_table_row(self, values: List[str], widths: List[int]) -> str:
        """Format a table row with proper column widths."""
        cells = []
        for value, width in zip(values, widths):
            cells.append(value.ljust(width))
        return '| ' + ' | '.join(cells) + ' |'

    def format_separator(self, widths: List[int]) -> str:
        """Format a separator line for the table."""
        return '|' + '|'.join(['-' * (w + 2) for w in widths]) + '|'

    def format_markdown_table(self, stats_data: List[Dict], headers: List[str]) -> str:
        """Generate a markdown-formatted table."""
        lines = []

        # Header row
        header_line = '| ' + ' | '.join(headers) + ' |'
        lines.append(header_line)

        # Separator row
        separator = '|' + '|'.join([' --- ' for _ in headers]) + '|'
        lines.append(separator)

        # Data rows
        total_ballots = 0
        total_unique = 0
        total_cvr_size = 0.0
        total_blt_size = 0.0

        for stats in stats_data:
            reduction_pct = (stats['blt_profile_size_kb'] / stats['cvr_size_kb'] * 100) if stats['cvr_size_kb'] > 0 else 0

            row = [
                stats['contest'],
                str(stats['seats']),
                str(stats['candidates']),
                f"{stats['ballots']:,}",
                f"{stats['unique_rankings']:,}",
                f"{stats['cvr_size_kb']:.1f}",
                f"{stats['blt_profile_size_kb']:.1f}",
                f"{reduction_pct:.1f}%"
            ]
            lines.append('| ' + ' | '.join(row) + ' |')

            total_ballots += stats['ballots']
            total_unique += stats['unique_rankings']
            total_cvr_size += stats['cvr_size_kb']
            total_blt_size += stats['blt_profile_size_kb']

        # Totals row
        total_reduction_pct = (total_blt_size / total_cvr_size * 100) if total_cvr_size > 0 else 0
        totals_row = [
            '**TOTAL**',
            '-',
            '-',
            f"**{total_ballots:,}**",
            f"**{total_unique:,}**",
            f"**{total_cvr_size:.1f}**",
            f"**{total_blt_size:.1f}**",
            f"**{total_reduction_pct:.1f}%**"
        ]
        lines.append('| ' + ' | '.join(totals_row) + ' |')

        return '\n'.join(lines)

    def generate_table(self):
        """Generate and display the statistics table."""
        print("\nGenerating contest statistics...\n")

        # Collect statistics for all contests
        stats_data = []

        for contest_name, district_num in self.contests:
            print(f"Processing {contest_name}...")

            # Get CVR statistics
            num_ballots, num_candidates, cvr_size_kb = self.get_cvr_stats(district_num)

            # Get unique rankings from abstract
            num_unique_rankings = self.get_unique_rankings_from_abstract(district_num)

            # Generate BLT format ranking profile
            _, blt_profile_size_kb = self.generate_ranking_profile_blt(district_num)

            stats_data.append({
                'contest': contest_name,
                'seats': self.num_seats,
                'candidates': num_candidates,
                'ballots': num_ballots,
                'unique_rankings': num_unique_rankings,
                'cvr_size_kb': cvr_size_kb,
                'blt_profile_size_kb': blt_profile_size_kb
            })

        print("\n" + "="*140)
        print("CONTEST STATISTICS TABLE")
        print("="*140 + "\n")

        # Define column headers and widths
        headers = [
            'Contest Name',
            'Winners',
            'Candidates',
            'Ballots',
            'Unique Rankings',
            'CVR Size (KB)',
            'Profile Size (KB)',
            'Reduction %'
        ]

        # Calculate column widths
        widths = [
            max(20, len(headers[0])),  # Contest Name
            max(7, len(headers[1])),   # Winners
            max(10, len(headers[2])),  # Candidates
            max(10, len(headers[3])),  # Ballots
            max(15, len(headers[4])),  # Unique Rankings
            max(14, len(headers[5])),  # CVR Size
            max(17, len(headers[6])),  # Profile Size
            max(12, len(headers[7]))   # Reduction %
        ]

        # Print header
        print(self.format_table_row(headers, widths))
        print(self.format_separator(widths))

        # Print data rows
        total_ballots = 0
        total_unique = 0
        total_cvr_size = 0.0
        total_profile_size = 0.0

        for stats in stats_data:
            # Calculate reduction percentage for BLT profile
            reduction_pct = (stats['blt_profile_size_kb'] / stats['cvr_size_kb'] * 100) if stats['cvr_size_kb'] > 0 else 0

            row = [
                stats['contest'],
                str(stats['seats']),
                str(stats['candidates']),
                f"{stats['ballots']:,}",
                f"{stats['unique_rankings']:,}",
                f"{stats['cvr_size_kb']:.1f}",
                f"{stats['blt_profile_size_kb']:.1f}",
                f"{reduction_pct:.1f}%"
            ]
            print(self.format_table_row(row, widths))

            total_ballots += stats['ballots']
            total_unique += stats['unique_rankings']
            total_cvr_size += stats['cvr_size_kb']
            total_profile_size += stats['blt_profile_size_kb']

        # Print totals
        print(self.format_separator(widths))
        total_reduction_pct = (total_profile_size / total_cvr_size * 100) if total_cvr_size > 0 else 0
        totals_row = [
            'TOTAL',
            '-',
            '-',
            f"{total_ballots:,}",
            f"{total_unique:,}",
            f"{total_cvr_size:.1f}",
            f"{total_profile_size:.1f}",
            f"{total_reduction_pct:.1f}%"
        ]
        print(self.format_table_row(totals_row, widths))
        print(self.format_separator(widths))

        # Print summary statistics
        print(f"\nSummary:")
        print(f"  Total contests: {len(stats_data)}")
        print(f"  Total ballots: {total_ballots:,}")
        print(f"  Total unique rankings: {total_unique:,}")
        print(f"  Total CVR size: {total_cvr_size:.1f} KB ({total_cvr_size/1024:.1f} MB)")
        print(f"  Total profile size: {total_profile_size:.1f} KB ({total_profile_size/1024:.1f} MB)")
        print(f"  Compression ratio: {(total_profile_size/total_cvr_size)*100:.1f}%")
        print(f"  Average unique rankings per contest: {total_unique/len(stats_data):,.0f}")
        print()

        # Save markdown table to file
        markdown_headers = [
            'Contest Name',
            'Winners',
            'Candidates',
            'Ballots',
            'Unique Rankings',
            'CVR Size (KB)',
            'BLT Profile (KB)',
            'Reduction %'
        ]
        markdown_table = self.format_markdown_table(stats_data, markdown_headers)

        # Create markdown file with table and summary
        markdown_file = self.base_dir / "contest_statistics.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write("# Contest Statistics\n\n")
            f.write("## Portland 2024 City Council Elections\n\n")
            f.write(markdown_table)
            f.write("\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total contests:** {len(stats_data)}\n")
            f.write(f"- **Total ballots:** {total_ballots:,}\n")
            f.write(f"- **Total unique rankings:** {total_unique:,}\n")
            f.write(f"- **Total CVR size:** {total_cvr_size:.1f} KB ({total_cvr_size/1024:.1f} MB)\n")
            f.write(f"- **Total BLT profile size:** {total_profile_size:.1f} KB ({total_profile_size/1024:.1f} MB)\n")
            f.write(f"- **Compression ratio:** {(total_profile_size/total_cvr_size)*100:.1f}%\n")
            f.write(f"- **Space savings:** {((total_cvr_size-total_profile_size)/total_cvr_size)*100:.1f}%\n")
            f.write(f"- **Average unique rankings per contest:** {total_unique/len(stats_data):,.0f}\n")
            f.write("\n## File Formats\n\n")
            f.write("### BLT Format\n\n")
            f.write("A compact ballot format widely used for ranked-choice voting analysis:\n\n")
            f.write("- First line: `number_of_candidates number_of_seats`\n")
            f.write("- Ballot lines: `count candidate1 candidate2 ... 0`\n")
            f.write("- End marker: `0`\n")
            f.write("- Candidate names in quotes\n")
            f.write("- Election title in quotes\n")
            f.write("\n### File Locations\n\n")
            f.write(f"- **BLT profiles:** `{self.profiles_dir.name}/Portland_D{{1-4}}_ranking_profile.blt`\n")
            f.write(f"- **CVR files:** `{self.raw_csv_dir.name}/Portland_D{{1-4}}_raw_votekit_format.csv`\n")
            f.write(f"- **Abstract files:** `{self.abstracts_dir.name}/Portland_D{{1-4}}_abstract.txt`\n")

        print(f"\n" + "="*80)
        print(f"Markdown table saved to: {markdown_file}")
        print(f"Ranking profile BLT files saved to: {self.profiles_dir}/")
        print("="*80)
        print()


def main():
    """Main entry point."""
    stats = ContestStatistics()
    stats.generate_table()


if __name__ == '__main__':
    main()
