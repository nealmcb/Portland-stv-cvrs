# SF CVR Processing Pipeline

Process San Francisco Dominion JSON CVR exports to generate CSV format CVRs, BLT preference profiles, and contest statistics.

## Features

- **Streaming JSON parsing** - handles large CVR files efficiently
- **Deterministic output** - stable ordering, reproducible results
- **Restartable** - caches downloads and extractions
- **CSV export** - Dominion-style format compatible with Colorado CVRs
- **BLT generation** - compact preference profile format
- **Statistics** - compression ratios, unique rankings, file sizes

## Installation

No external dependencies required - uses Python 3 stdlib only.

```bash
cd "/srv/s/ranked-choice/profile-generator/Portland-stv-cvrs/Restructured Repo/CVRs"
```

## Usage

### Complete Pipeline

Process an entire election in one command:

```bash
python -m sf_cvr all 20241105 \
  --cvr-url https://www.sfelections.org/results/20241105/data/20241203/CVR_Export_20241202143051.zip
```

### Step-by-Step

Run each step individually:

```bash
# Step 1: Fetch and extract CVR ZIP
python -m sf_cvr fetch 20241105 \
  --cvr-url https://www.sfelections.org/results/20241105/data/20241203/CVR_Export_20241202143051.zip

# Step 2: Export contests to CSV
python -m sf_cvr export 20241105

# Step 3: Generate BLT and statistics
python -m sf_cvr stats 20241105
```

### Options

- `--rcv-only` - Only process ranked-choice voting contests (default: all contests)
- `--output-dir DIR` - Custom output directory (default: `CVRs/sf_{election_id}`)

## Output Structure

```
CVRs/sf_20241105/
├── cache/
│   └── CVR_Export_20241202143051.zip    # Downloaded CVR ZIP
├── extracted/
│   ├── ContestManifest.json             # Extracted manifest files
│   ├── CandidateManifest.json
│   └── CvrExport_*.json                 # Extracted CVR files
├── cvr_all_contests.csv                 # Unified CSV with all contests
├── ranking_profiles/
│   ├── sf_20241105_mayor.blt            # BLT preference profiles
│   ├── sf_20241105_board-of-supervisors-district-1.blt
│   └── ...
└── contest_statistics.md                # Markdown table with stats
```

## CSV Format

The unified CSV file follows the Dominion format used in Colorado, with all contests in a single file:

- **Row 1:** Column headers (metadata + all contest/candidate columns)
- **Metadata columns:** `CvrNumber`, `TabulatorNum`, `BatchId`, `RecordId`, `BallotType`
- **Contest columns:** For RCV contests, each candidate appears once per rank
- **Format:** `Contest Name - Candidate Name(Rank)` for RCV, `Contest Name - Candidate Name` for non-RCV

Example for RCV contest with 3 candidates and 5 ranks:

```csv
CvrNumber,TabulatorNum,BatchId,RecordId,BallotType,MAYOR - Alice(1),MAYOR - Bob(1),MAYOR - Carol(1),MAYOR - Alice(2),MAYOR - Bob(2),...
1,5,1,X,25,1,0,0,0,1,...
```

## BLT Format

BLT files contain preference profiles (unique rankings with counts):

```
18 1                          # 18 candidates, 1 seat
1095 9 0                      # 1095 ballots: candidate 9 only
522 1 2 16 0                  # 522 ballots: candidates 1, 2, 16
...
0                             # End marker
"DANIEL LURIE"                # Candidate 1
"MARK FARRELL"                # Candidate 2
...
"MAYOR"                       # Contest title
```

## Performance

- **SF November 2024:** ~400K ballots, 11 RCV contests
- **Processing time:** ~60 seconds (full pipeline)
- **Memory usage:** ~1 GB peak
- **Compression:** BLT files are typically 5-15% the size of CSV CVRs

## Implementation Notes

### Streaming JSON Parser

The CVR parser uses Python's built-in `json` module with file-by-file processing to avoid loading the entire dataset into memory. CVR export files are processed sequentially.

### Candidate Ordering

Candidates are sorted by ID within each contest for deterministic output. This ensures stable column ordering in CSV files and consistent candidate numbering in BLT files.

### Write-in Handling

Write-in candidates are excluded from CSV and BLT exports. They are tracked in the manifest but not included in preference profiles.

### Contest Identification

Ranked-choice contests are identified by `NumOfRanks > 0` in the ContestManifest. Non-RCV contests have `NumOfRanks = 0`.

## Module Structure

```
sf_cvr/
├── __init__.py           # Package initialization
├── __main__.py           # Make module executable
├── cli.py                # Command-line interface
├── fetch.py              # Download and cache CVR ZIP
├── manifests.py          # Parse manifest files
├── parse_dominion.py     # Stream parse CVR JSON
├── export_csv.py         # Export to CSV format
├── stats.py              # Generate BLT and statistics
└── README.md             # This file
```

## Known Limitations

- **URL Auto-Discovery:** Not yet implemented. Users must provide `--cvr-url` explicitly.
- **Memory:** All ballots are loaded into memory during CSV export (required for per-contest iteration).
- **Write-ins:** Excluded from current implementation.

## Examples

### SF November 2024 Election

Test with the known CVR URL:

```bash
python -m sf_cvr all 20241105 \
  --cvr-url https://www.sfelections.org/results/20241105/data/20241203/CVR_Export_20241202143051.zip \
  --rcv-only
```

This will process all 11 RCV contests (Mayor + 10 Board of Supervisors districts) and generate:
- 1 unified CSV CVR file with all contests
- 11 BLT ranking profile files (in `ranking_profiles/` directory)
- 1 statistics table

### Custom Output Directory

```bash
python -m sf_cvr all 20241105 \
  --cvr-url https://...CVR_Export.zip \
  --output-dir /tmp/sf_test
```

## License

Part of the Portland RCV profile generator project.
