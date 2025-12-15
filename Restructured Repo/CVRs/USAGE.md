# Usage Guide: Generating Printable Vote Abstracts

This guide explains how to use the scripts in this directory to generate and verify lossless, printable abstracts of ranked-choice election votes.

## Prerequisites

### Required Python Packages

```bash
pip install pandas
```

No other dependencies are required for generating or verifying the abstracts.

## Quick Start

Generate abstracts for all four districts:

```bash
cd "Restructured Repo/CVRs"
python3 3_generate_abstracts.py
```

Verify that abstracts are lossless:

```bash
python3 4_verify_abstracts.py
```

## Scripts Overview

### 1. `3_generate_abstracts.py`

**Purpose**: Generate prefix-compressed, printable abstracts from CVR data.

**Input**: CSV files in `raw_votekit_csv/Portland_D{1-4}_raw_votekit_format.csv`

**Output**: Plain text abstracts in `abstracts/Portland_D{1-4}_abstract.txt`

**Usage**:
```bash
python3 3_generate_abstracts.py
```

The script will:
1. Read ballot data from all four district CSV files
2. Build preference profiles (ranking → count)
3. Sort rankings lexicographically by candidate order
4. Apply prefix compression to group similar rankings
5. Generate plain text abstracts with:
   - Contest metadata (district, seats, ballot counts)
   - Candidate legend (ID ↔ name mapping)
   - Prefix-compressed ranking table
   - Verification statistics

**Processing time**: ~30 seconds for all four districts

**Output size**: ~140,000 lines total across all districts

### 2. `4_verify_abstracts.py`

**Purpose**: Verify that generated abstracts are lossless representations of original CVR data.

**Input**: 
- Original CSVs: `raw_votekit_csv/Portland_D{1-4}_raw_votekit_format.csv`
- Generated abstracts: `abstracts/Portland_D{1-4}_abstract.txt`

**Output**: Console report showing verification results

**Usage**:
```bash
python3 4_verify_abstracts.py
```

The script will:
1. Load original ballot data
2. Parse generated abstracts
3. Compare ballot counts and ranking expressions
4. Report any discrepancies

**Expected output**:
```
============================================================
SUMMARY
============================================================
District 1: ✅ PASSED
District 2: ✅ PASSED
District 3: ✅ PASSED
District 4: ✅ PASSED

🎉 All abstracts verified as lossless!
```

**Processing time**: ~1 minute for all four districts

## Understanding the Output

### Abstract File Structure

Each abstract file (`Portland_D{N}_abstract.txt`) contains:

#### 1. Header
```
================================================================================
ABSTRACT OF VOTES - CITY COUNCIL DISTRICT 1
City of Portland, Oregon
November 2024 General Election
================================================================================
```

#### 2. Contest Information
```
CONTEST INFORMATION
--------------------------------------------------------------------------------
Contest: City Council District 1
Election Method: Single Transferable Vote (STV)
Seats: 3
Total Ballots with Rankings: 43669
Unique Ranking Expressions: 18895
```

#### 3. Candidate Legend
Maps short IDs (C01, C02, ...) to full candidate names:
```
CANDIDATE LEGEND
--------------------------------------------------------------------------------
C01  Candace Avalos
C02  Cayle Tern
C03  David Linn
...
```

#### 4. Explanation Section
Documents the format and compression method.

#### 5. Preference Profile (PREFIX-COMPRESSED)

The core data showing all rankings and their counts:

**Example without prefix**:
```
C01 > C03 > C09 : 152
```
Means: 152 ballots ranked C01 first, C03 second, C09 third.

**Example with prefix compression**:
```
PREFIX: C01 > C03
--------------------------------------------------------------------------------
  (exact match) : 45
  ... > C09 : 152
  ... > C09 > C06 : 38
```

Means:
- 45 ballots: `C01 > C03` (exact match, nothing more)
- 152 ballots: `C01 > C03 > C09`
- 38 ballots: `C01 > C03 > C09 > C06`

#### 6. Footer
```
================================================================================
END OF ABSTRACT
Total ranking expressions: 18895
Total ballots: 43669
================================================================================
```

## Printing the Abstracts

### Estimated Page Counts

| District | Lines  | Pages (60 lines/page) |
|----------|--------|-----------------------|
| D1       | 19,002 | 317                   |
| D2       | 41,240 | 687                   |
| D3       | 40,867 | 681                   |
| D4       | 38,421 | 640                   |

### Printing Commands

**Single column (standard)**:
```bash
lpr abstracts/Portland_D1_abstract.txt
```

**Two-column layout** (saves ~50% paper):
```bash
pr -2 -t -w 160 abstracts/Portland_D1_abstract.txt | lpr
```

**Three-column layout** (saves ~66% paper):
```bash
pr -3 -t -w 240 abstracts/Portland_D1_abstract.txt | lpr
```

### Recommended Print Settings

- **Font**: Monospace (Courier, Consolas, or similar)
- **Font size**: 10pt (2-column) or 8pt (3-column)
- **Paper**: Letter (8.5" × 11") or A4
- **Margins**: 0.5" all sides for multi-column
- **Line spacing**: Single
- **Duplex**: Recommended to save paper

## Modifying the Scripts

### Changing Compression Parameters

In `3_generate_abstracts.py`, the `RankingAbstract` class has configuration constants:

```python
MIN_GROUP_SIZE = 20  # Minimum rankings needed to form a prefix group
MAX_LOOKAHEAD = 200  # Maximum lookahead for finding optimal prefix groups
```

**MIN_GROUP_SIZE**: Controls how aggressively the algorithm groups rankings.
- **Increase** (e.g., 50) for less compression but simpler output
  - Fewer prefix groups, easier to read
  - More lines in output, uses more paper
- **Decrease** (e.g., 10) for more compression but more complex output
  - More prefix groups, more compressed
  - Fewer lines in output, saves paper
  - Trade-off: harder to navigate manually

**MAX_LOOKAHEAD**: Performance optimization for large datasets.
- Limits how far ahead the algorithm looks when finding prefix groups
- Higher values may find better compression but take longer
- Current value (200) provides good balance for Portland data

### Changing Candidate ID Format

In `3_generate_abstracts.py`, line ~195:

```python
candidate_to_id = {c: f"C{i+1:02d}" for i, c in enumerate(candidate_order)}
```

Change the format string to customize IDs:
- `f"C{i+1:03d}"` → C001, C002, C003, ...
- `f"{i+1:02d}"` → 01, 02, 03, ... (no C prefix)
- Use full names: `{c: c for c in candidate_order}` (no IDs)

### Adding Additional Metadata

In `generate_abstract()` method, add lines to the header section after line 202:

```python
f.write("Your custom metadata here\n")
```

## Troubleshooting

### Problem: "FileNotFoundError: raw_votekit_csv/..."

**Solution**: Make sure you're running the scripts from the `Restructured Repo/CVRs/` directory.

```bash
cd "Restructured Repo/CVRs"
python3 3_generate_abstracts.py
```

### Problem: "ModuleNotFoundError: No module named 'pandas'"

**Solution**: Install required dependencies.

```bash
pip install pandas
```

Note: pandas is only needed for the data cleaning scripts (`1_reformat_csvs.py`, `2_clean_profiles.py`), not for generating or verifying abstracts.

### Problem: Verification fails with count mismatches

**Solution**: Regenerate the abstracts and verify again.

```bash
python3 3_generate_abstracts.py
python3 4_verify_abstracts.py
```

If the problem persists, check that the CSV files haven't been modified.

### Problem: Output files are too large

**Solution**: The abstracts are intentionally uncompressed for human readability. For storage, you can compress them:

```bash
gzip abstracts/*.txt
```

To view compressed files:
```bash
zcat abstracts/Portland_D1_abstract.txt.gz | less
```

## Use Cases

### For Election Officials

Generate official archival records:
```bash
python3 3_generate_abstracts.py
python3 4_verify_abstracts.py
# Print or archive the abstracts/ directory
```

### For Auditors

Verify election results independently:
1. Obtain CVR data
2. Generate abstracts with this script
3. Compare with official results
4. Use verification script to prove losslessness

### For Researchers

Analyze voting patterns:
```bash
# Generate abstracts
python3 3_generate_abstracts.py

# Parse abstracts for analysis
python3 << 'EOF'
import re

with open('abstracts/Portland_D1_abstract.txt', 'r') as f:
    content = f.read()
    
# Extract all ranking expressions and counts
for match in re.finditer(r'(C\d+[^:]+): (\d+)', content):
    ranking, count = match.groups()
    # Your analysis code here
    print(f"{ranking}: {count}")
EOF
```

### For Legal Proceedings

Generate certified evidence:
1. Run verification script to prove losslessness
2. Print abstracts on archival-quality paper
3. Notarize or certify printed documents
4. Store in permanent records

## Additional Resources

- **Full documentation**: See [abstracts/README.md](abstracts/README.md)
- **Data source**: Original CVR data is in `raw_votekit_csv/`
- **Data cleaning**: See `2_clean_profiles.py` for cleaning rules

## Support

For questions or issues:
1. Check the documentation in `abstracts/README.md`
2. Review the script source code (well-commented)
3. Open an issue in the repository

## Version History

- **v1.0** (December 2024): Initial release
  - Prefix compression algorithm
  - Lossless verification
  - Plain text output optimized for printing
