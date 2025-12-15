# CVRs

## Processing Pipeline

1. **Reformat CSVs** (`1_reformat_csvs.py`): Reformat the cast vote records released by the city of Portland to match the format required by VoteKit.

2. **Clean Profiles** (`2_clean_profiles.py`): Clean the profiles of overvotes, undervotes, and certain write-ins and pickle the profiles for analysis.

3. **Generate Abstracts** (`3_generate_abstracts.py`): Generate prefix-compressed, printable, lossless abstracts of votes suitable for long-term archival on paper.

4. **Verify Abstracts** (`4_verify_abstracts.py`): Verify that the generated abstracts are lossless representations of the original CVR data.

## Output Files

- `raw_votekit_csv/` - Reformatted CVR data in VoteKit format
- `cleaned_votekit_profiles/` - Cleaned preference profiles (pickled)
- `abstracts/` - **Printable vote abstracts for archival** (see [abstracts/README.md](abstracts/README.md))
- `official_city_results/` - Official tabulation results from the city

## Printable Vote Abstracts

The `abstracts/` directory contains human-readable, paper-archivable abstracts of all votes cast in each district. These abstracts are:

- **Lossless**: Enable exact reconstruction of election tallies
- **Deterministic**: Same input always produces same output  
- **Human-readable**: Plain ASCII text, no special tools required
- **Vendor-neutral**: Independent of any voting system vendor
- **Compact**: Prefix compression optimizes for printing

Each abstract includes:
- Complete candidate roster with ID mappings
- All unique ranking expressions and their counts
- Prefix-compressed format to reduce paper usage
- Verification information proving losslessness

**Example use cases:**
- Official record for election archives
- Basis for manual recounts
- Evidence in audits or legal proceedings  
- Historical research and analysis

See [abstracts/README.md](abstracts/README.md) for complete documentation including:
- Format specification
- Sorting and compression algorithms
- Print specifications and page estimates
- Verification of lossless property
- Usage instructions for different audiences

**Quick stats:**
- District 1: 43,669 ballots → 19,002 lines (317 pages)
- District 2: 77,686 ballots → 41,240 lines (687 pages)
- District 3: 85,115 ballots → 40,867 lines (681 pages)
- District 4: 77,332 ballots → 38,421 lines (640 pages)