# Restructured Repo

We restructured the pieces of the original repo that could be done with VoteKit. 

## Directories

- **Analysis** - Performs the analysis done in the report
- **CVRs** - Cleans and processes the cast vote records from the city
  - **NEW**: Includes printable vote abstracts for archival (see [CVRs/abstracts/](CVRs/abstracts/))
- **Sandbox** - Code that did not make the final paper
- **Shapefiles** - Contains relevant Portland geometries

## Printable Vote Abstracts

The `CVRs/abstracts/` directory contains **lossless, human-readable abstracts** of all votes cast in the Portland 2025 ranked-choice elections. These are designed for:

- Long-term paper archival
- Manual recounts and audits  
- Legal proceedings and historical research
- Vendor-neutral verification

Key features:
- ✅ **Lossless**: Exact reconstruction of tallies possible
- ✅ **Deterministic**: Same input always produces same output
- ✅ **Compact**: Prefix compression reduces from 283K ballots to ~140K lines
- ✅ **Plain text**: ASCII only, no special tools required

See [CVRs/abstracts/README.md](CVRs/abstracts/README.md) for complete documentation.

## Version Info

This code was done with VoteKit version 3.2.0.
