#!/usr/bin/env python3
"""
Fetch and cache SF CVR ZIP files.
"""

import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
import sys


def fetch_cvr_zip(
    election_id: str,
    cvr_url: Optional[str] = None,
    cache_dir: Optional[Path] = None
) -> Path:
    """
    Download and cache CVR ZIP file.

    Args:
        election_id: Election date in YYYYMMDD format (e.g., "20241105")
        cvr_url: Direct URL to CVR ZIP (optional)
        cache_dir: Directory to cache downloaded files (default: CVRs/sf_{election_id}/cache)

    Returns:
        Path to cached ZIP file
    """
    if cache_dir is None:
        cache_dir = Path(f"CVRs/sf_{election_id}/cache")

    cache_dir.mkdir(parents=True, exist_ok=True)

    # If no URL provided, try to discover it
    if cvr_url is None:
        cvr_url = discover_cvr_url(election_id)
        if cvr_url is None:
            raise ValueError(
                f"Could not auto-discover CVR URL for election {election_id}. "
                "Please provide --cvr-url explicitly."
            )

    # Determine filename from URL
    filename = cvr_url.split('/')[-1]
    if not filename.endswith('.zip'):
        filename = f"CVR_Export_{election_id}.zip"

    zip_path = cache_dir / filename

    # Check if already cached
    if zip_path.exists():
        print(f"Using cached CVR ZIP: {zip_path}")
        return zip_path

    # Download
    print(f"Downloading CVR ZIP from: {cvr_url}")
    print(f"Saving to: {zip_path}")

    try:
        with urllib.request.urlopen(cvr_url) as response:
            total_size = int(response.headers.get('content-length', 0))

            with open(zip_path, 'wb') as f:
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB chunks

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r  Downloaded: {mb_down:.1f}/{mb_total:.1f} MB ({pct:.1f}%)", end='', file=sys.stderr)

        print()  # New line after progress
        print(f"Download complete: {zip_path}")
        return zip_path

    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to download CVR ZIP: {e}")


def discover_cvr_url(election_id: str) -> Optional[str]:
    """
    Attempt to discover CVR URL from sfelections.org.

    Args:
        election_id: Election date in YYYYMMDD format

    Returns:
        CVR ZIP URL if found, None otherwise

    Note:
        This is a best-effort implementation. SF election data URLs
        don't follow a consistent pattern, so auto-discovery may fail.
        In that case, users must provide --cvr-url explicitly.
    """
    # Try common URL patterns
    year = election_id[:4]
    month = election_id[4:6]
    day = election_id[6:8]

    # Pattern 1: Direct results data directory
    # https://www.sfelections.org/results/{election_id}/data/
    base_url = f"https://www.sfelections.org/results/{election_id}/data/"

    print(f"Attempting to discover CVR URL from: {base_url}")
    print("Note: Auto-discovery may fail. If so, provide --cvr-url explicitly.")

    # TODO: Implement HTML scraping to find CVR ZIP link
    # For now, return None to force explicit URL
    return None


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 2:
        print("Usage: fetch.py <election_id> [cvr_url]")
        sys.exit(1)

    election_id = sys.argv[1]
    cvr_url = sys.argv[2] if len(sys.argv) > 2 else None

    zip_path = fetch_cvr_zip(election_id, cvr_url)
    print(f"CVR ZIP: {zip_path}")
