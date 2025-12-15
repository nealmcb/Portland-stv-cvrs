#!/usr/bin/env python3
"""
Verification script to prove losslessness of generated abstracts.

This script:
1. Reads the original CVR data
2. Reads the generated abstract
3. Verifies that all ballots are accounted for
4. Confirms that ballot counts match exactly
"""

import csv
import re
from pathlib import Path
from collections import Counter


def load_cvr_ballots(csv_path):
    """Load ballots from original CVR CSV file."""
    ballots = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            ranking = []
            for i in range(1, 7):
                rank_col = f'Rank {i}'
                candidate = row.get(rank_col, '').strip()
                # Skip empty, overvotes, and write-ins (matching the cleaning rules)
                if candidate and candidate != 'overvote' and not candidate.startswith('Write-in-'):
                    # Avoid duplicate candidates in same ballot
                    if candidate not in ranking:
                        ranking.append(candidate)
            
            ballots.append(tuple(ranking))
    
    return ballots


def load_abstract_profile(abstract_path):
    """Parse the generated abstract file and extract preference profile."""
    candidate_legend = {}
    profile = {}
    
    with open(abstract_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Parse candidate legend
    in_legend = False
    for i, line in enumerate(lines):
        if line.startswith('CANDIDATE LEGEND'):
            in_legend = True
            continue
        
        if in_legend:
            if line.strip() == '' or line.startswith('EXPLANATION'):
                in_legend = False
                continue
            
            if line.startswith('-' * 40):
                continue
            
            # Parse legend line: "C01  Candace Avalos"
            match = re.match(r'(C\d+)\s+(.+)$', line.strip())
            if match:
                cid, name = match.groups()
                candidate_legend[cid] = name.strip()
    
    # Parse preference profile
    in_profile = False
    current_prefix = []
    
    for line in lines:
        if line.startswith('PREFERENCE PROFILE'):
            in_profile = True
            continue
        
        if line.startswith('END OF ABSTRACT'):
            break
        
        if not in_profile:
            continue
        
        # Check for prefix line
        if line.startswith('PREFIX:'):
            # Parse prefix: "PREFIX: C01 > C03"
            prefix_str = line.replace('PREFIX:', '').strip()
            if prefix_str:
                current_prefix = [cid.strip() for cid in prefix_str.split('>')]
            else:
                current_prefix = []
            continue
        
        # Parse ranking line
        # Format: "C01 > C03 > C09 : 152"
        # Or with prefix: "  ... > C09 : 152"
        # Or exact match: "  (exact match) : 45"
        # Or empty: "(empty) : 798"
        
        if ':' in line:
            parts = line.split(':')
            if len(parts) == 2:
                ranking_str = parts[0].strip()
                count_str = parts[1].strip()
                
                try:
                    count = int(count_str)
                except ValueError:
                    continue
                
                # Parse ranking
                if ranking_str == '(empty)':
                    ranking = ()
                elif ranking_str == '(exact match)':
                    # Use current prefix as exact ranking
                    ranking = tuple(current_prefix)
                elif ranking_str.startswith('...'):
                    # Suffix after prefix
                    suffix_str = ranking_str.replace('...', '').replace('>', ' ').strip()
                    if suffix_str:
                        suffix = [cid.strip() for cid in suffix_str.split() if cid.strip()]
                        ranking = tuple(current_prefix + suffix)
                    else:
                        ranking = tuple(current_prefix)
                else:
                    # Full ranking
                    ranking = tuple([cid.strip() for cid in ranking_str.split('>') if cid.strip()])
                
                # Convert IDs back to candidate names
                if ranking:
                    ranking_names = tuple(candidate_legend[cid] for cid in ranking)
                else:
                    ranking_names = ()
                
                profile[ranking_names] = count
    
    return profile, candidate_legend


def verify_district(district):
    """Verify a single district's abstract against original CVR."""
    print(f"\nVerifying District {district}...")
    print("-" * 60)
    
    base_path = Path(__file__).parent
    csv_path = base_path / f"raw_votekit_csv/Portland_D{district}_raw_votekit_format.csv"
    abstract_path = base_path / f"abstracts/Portland_D{district}_abstract.txt"
    
    # Load original ballots
    print("Loading original CVR data...")
    original_ballots = load_cvr_ballots(csv_path)
    original_profile = Counter(original_ballots)
    
    # Load abstract
    print("Loading generated abstract...")
    abstract_profile, candidate_legend = load_abstract_profile(abstract_path)
    
    # Compare
    print("\nComparison:")
    print(f"  Original ballots: {len(original_ballots)}")
    print(f"  Original unique rankings: {len(original_profile)}")
    print(f"  Abstract unique rankings: {len(abstract_profile)}")
    print(f"  Candidates in legend: {len(candidate_legend)}")
    
    # Check if all rankings match
    original_set = set(original_profile.keys())
    abstract_set = set(abstract_profile.keys())
    
    missing_in_abstract = original_set - abstract_set
    extra_in_abstract = abstract_set - original_set
    
    if missing_in_abstract:
        print(f"\n❌ ERROR: {len(missing_in_abstract)} rankings missing in abstract")
        for ranking in list(missing_in_abstract)[:5]:
            print(f"    Missing: {ranking}")
    elif extra_in_abstract:
        print(f"\n❌ ERROR: {len(extra_in_abstract)} extra rankings in abstract")
        for ranking in list(extra_in_abstract)[:5]:
            print(f"    Extra: {ranking}")
    else:
        print("  ✓ All rankings present in abstract")
    
    # Check if counts match
    count_mismatches = 0
    total_original = 0
    total_abstract = 0
    
    for ranking in original_set:
        orig_count = original_profile[ranking]
        abst_count = abstract_profile.get(ranking, 0)
        
        total_original += orig_count
        total_abstract += abst_count
        
        if orig_count != abst_count:
            count_mismatches += 1
            if count_mismatches <= 5:
                print(f"  ❌ Count mismatch for {ranking}: orig={orig_count}, abstract={abst_count}")
    
    if count_mismatches > 0:
        print(f"\n❌ ERROR: {count_mismatches} count mismatches")
    else:
        print("  ✓ All counts match exactly")
    
    print(f"\nTotal ballot verification:")
    print(f"  Original total: {total_original}")
    print(f"  Abstract total: {total_abstract}")
    
    if total_original == total_abstract:
        print("  ✓ Total ballots match")
    else:
        print(f"  ❌ ERROR: Total mismatch ({total_abstract - total_original})")
    
    # Overall verdict
    if (len(missing_in_abstract) == 0 and 
        len(extra_in_abstract) == 0 and 
        count_mismatches == 0 and 
        total_original == total_abstract):
        print("\n✅ VERIFICATION PASSED: Abstract is lossless")
        return True
    else:
        print("\n❌ VERIFICATION FAILED: Abstract has discrepancies")
        return False


def main():
    """Verify all four district abstracts."""
    print("=" * 60)
    print("ABSTRACT VERIFICATION")
    print("=" * 60)
    print("\nThis script verifies that the generated abstracts are")
    print("lossless representations of the original CVR data.")
    
    districts = [1, 2, 3, 4]
    results = {}
    
    for district in districts:
        results[district] = verify_district(district)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for district, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"District {district}: {status}")
    
    if all(results.values()):
        print("\n🎉 All abstracts verified as lossless!")
        return 0
    else:
        print("\n⚠️  Some abstracts failed verification")
        return 1


if __name__ == "__main__":
    exit(main())
