"""
Download FIA (Forest Inventory & Analysis) data for GA, AL, and SC.

Run from the project root:
    python data/download.py        # download all states
    pytest data/download.py        # test with a single state (GA)
"""

import os
import urllib.request
import zipfile

BASE_URL = "https://apps.fs.usda.gov/fia/datamart/CSV/{state}_CSV.zip"
STATES = ["GA", "AL", "SC"]
TABLES = ["TREE", "PLOT", "COND"]
DATA_DIR = os.path.join(os.path.dirname(__file__))


def download_and_extract(state: str) -> None:
    url = BASE_URL.format(state=state)
    zip_path = os.path.join(DATA_DIR, f"{state}_CSV.zip")

    # Check if all files for this state are already present
    targets = [f"{state}_{table}.csv" for table in TABLES]
    if all(os.path.exists(os.path.join(DATA_DIR, f)) for f in targets):
        print(f"[{state}] All files already present, skipping.")
        return

    # Download zip
    print(f"[{state}] Downloading from {url} ...")
    urllib.request.urlretrieve(url, zip_path)
    print(f"[{state}] Download complete.")

    # Extract only the tables we need
    with zipfile.ZipFile(zip_path, "r") as zf:
        all_names = zf.namelist()
        for table in TABLES:
            zip_name = f"{state}_{table}.csv"
            if zip_name not in all_names:
                print(f"[{state}] WARNING: {zip_name} not found in zip. Available: {all_names}")
                continue
            out_path = os.path.join(DATA_DIR, f"{state}_{table}.csv")
            with zf.open(zip_name) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            print(f"[{state}] Extracted -> {out_path}")

    # Clean up zip
    os.remove(zip_path)
    print(f"[{state}] Done.\n")


def test_download():
    """Smoke test: download and extract GA only, verify expected files exist."""
    download_and_extract("GA")
    for table in TABLES:
        path = os.path.join(DATA_DIR, f"GA_{table}.csv")
        assert os.path.exists(path), f"Expected file not found: {path}"
    print("test_download passed.")


if __name__ == "__main__":
    for state in STATES:
        download_and_extract(state)
    print("All downloads complete.")
