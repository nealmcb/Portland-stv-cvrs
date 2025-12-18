# Contest Statistics

## Portland 2024 City Council Elections

| Contest Name | Winners | Candidates | Ballots | Unique Rankings | CVR Size (KB) | BLT Profile (KB) | Reduction % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Portland District 1 | 3 | 17 | 43,669 | 18,895 | 2656.0 | 314.6 | 11.8% |
| Portland District 2 | 3 | 23 | 77,686 | 41,109 | 5584.1 | 725.3 | 13.0% |
| Portland District 3 | 3 | 31 | 85,115 | 40,704 | 6564.7 | 738.6 | 11.3% |
| Portland District 4 | 3 | 31 | 77,332 | 38,258 | 4986.2 | 698.4 | 14.0% |
| **TOTAL** | - | - | **283,802** | **138,966** | **19791.0** | **2477.0** | **12.5%** |

## Summary

- **Total contests:** 4
- **Total ballots:** 283,802
- **Total unique rankings:** 138,966
- **Total CVR size:** 19791.0 KB (19.3 MB)
- **Total BLT profile size:** 2477.0 KB (2.4 MB)
- **Compression ratio:** 12.5%
- **Space savings:** 87.5%
- **Average unique rankings per contest:** 34,742

## File Formats

### BLT Format

A compact ballot format widely used for ranked-choice voting analysis:

- First line: `number_of_candidates number_of_seats`
- Ballot lines: `count candidate1 candidate2 ... 0`
- End marker: `0`
- Candidate names in quotes
- Election title in quotes

### File Locations

- **BLT profiles:** `ranking_profiles/Portland_D{1-4}_ranking_profile.blt`
- **CVR files:** `raw_votekit_csv/Portland_D{1-4}_raw_votekit_format.csv`
- **Abstract files:** `abstracts/Portland_D{1-4}_abstract.txt`
