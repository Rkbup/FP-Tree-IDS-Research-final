"""
Download and prepare the CIC-IDS2017 dataset.

This script provides a convenience function for fetching the CIC-IDS2017 data set.  In
practice, the data is hosted by the Canadian Institute for Cybersecurity and can
be downloaded from their servers after agreeing to the terms of use.  The
function below demonstrates how one could download a tar archive via
HTTP and extract it into the `data/raw/` directory.  If the remote host is not
reachable or requires authentication, the user must download the data manually
and place it in the appropriate directory.

Usage:

```
python download_dataset.py
```

After running, the raw dataset files will reside in `data/raw/`.
"""

import os
import tarfile
from pathlib import Path
from urllib.parse import urlparse
import requests


def _download_file(url: str, dest_path: Path, chunk_size: int = 1024 * 1024) -> None:
    """Download a file from a URL to a local path with a progress bar.

    Args:
        url: The remote URL pointing to the file to download.
        dest_path: The local file path to save the downloaded content.
        chunk_size: Number of bytes to stream per request.
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total = int(response.headers.get('content-length', 0))
    with open(dest_path, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                downloaded += len(chunk)
                done = int(50 * downloaded / total) if total else 0
                print(f"\r[{'=' * done}{' ' * (50 - done)}] {downloaded / (1024 ** 2):.2f}MB", end='')
    print("\nDownload complete.")


def download_cic_ids2017() -> None:
    """Download and extract the CIC-IDS2017 dataset.

    The CIC‑IDS2017 dataset is quite large (tens of gigabytes) and is
    distributed as a compressed tar archive.  This function downloads the
    archive into the `data/raw/` directory and then extracts it there.  If
    the archive already exists, the download step is skipped.  If the data
    are already extracted, extraction is also skipped.

    Note: if the download fails due to network restrictions, please download
    the data manually from the CIC website:
    <https://www.unb.ca/cic/datasets/ids-2017.html> and extract it into
    `data/raw/`.
    """
    raw_dir = Path(__file__).resolve().parent / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive_url = 'https://www.unb.ca/cic/datasets/ids-2017.html'  # placeholder URL
    archive_name = urlparse(archive_url).path.split('/')[-1]
    archive_path = raw_dir / archive_name
    # Check if dataset archive is already downloaded
    if not archive_path.exists():
        print(f"Downloading CIC-IDS2017 dataset from {archive_url}...")
        try:
            _download_file(archive_url, archive_path)
        except Exception as e:
            print(f"Failed to download dataset: {e}")
            print("Please download the dataset manually and place it in the 'data/raw' directory.")
            return
    else:
        print("Dataset archive already exists; skipping download.")
    # Extract
    try:
        extract_flag = False
        with tarfile.open(archive_path, 'r:gz') as tar:
            members = tar.getmembers()
            # Determine if extraction necessary by checking for one file
            for member in members:
                dest_file = raw_dir / member.name
                if not dest_file.exists():
                    extract_flag = True
                    break
            if extract_flag:
                print("Extracting dataset archive...")
                tar.extractall(path=raw_dir)
                print("Extraction complete.")
            else:
                print("Dataset already extracted; skipping extraction.")
    except Exception as e:
        print(f"Failed to extract archive: {e}")


if __name__ == '__main__':
    download_cic_ids2017()