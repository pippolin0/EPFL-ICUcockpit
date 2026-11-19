#!/usr/bin/env python3
"""Download and extract the pinned DOSE-I v2 dataset (standard library only)."""

import argparse
import hashlib
import json
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile


RECORD_ID = "22145442"
RECORD_URL = f"https://zenodo.org/records/{RECORD_ID}"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
# (archive name, enclosing directory in ZIP, local directory, Zenodo MD5)
ARCHIVES = (
    ("data.zip", "data", "raw", "b98c8a81d2e866085f9e7ac75a950754"),
    ("pEEG.zip", "pEEG", "pEEG", "431eea0808867c709d4cae0c25fad55f"),
    ("metadata.zip", "metadata", "metadata", "5c6292ff0bbb9bc92c92dc3aec44bf25"),
    ("static.zip", "static", "static", "1acb99f7b1c579a21a671f5dda3a14fe"),
    ("artifacts.zip", "artifacts", "artifacts", "0c6cfbde3e1293fcdd59cca68cd4e69e"),
    ("plots.zip", "plots", "plots", "abf5814ad9945ddfcc013b90ddde9390"),
)
MARKER = ".dose-i-complete.json"
CHUNK_SIZE = 1024 * 1024


def md5(path):
    """Match Zenodo's integrity checksum; MD5 is not used for security."""
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, target, checksum):
    """Cache only verified downloads; an interrupted .part is never reused."""
    if target.is_file() and md5(target) == checksum:
        print(f"Using verified archive: {target.name}", flush=True)
        return
    partial = target.with_suffix(target.suffix + ".part")
    request = Request(url, headers={"User-Agent": "EPFL-ICUcockpit-dataset-downloader/1.0"})
    try:
        with urlopen(request, timeout=60) as response, partial.open("wb") as output:
            total = response.headers.get("Content-Length")
            downloaded = 0
            last_report = -1
            while chunk := response.read(CHUNK_SIZE):
                output.write(chunk)
                downloaded += len(chunk)
                report = downloaded // (10 * CHUNK_SIZE)
                if report != last_report:
                    suffix = f" / {int(total) / CHUNK_SIZE:.1f} MiB" if total else " MiB"
                    print(f"  {target.name}: {downloaded / CHUNK_SIZE:.1f}{suffix}", flush=True)
                    last_report = report
        actual = md5(partial)
        if actual != checksum:
            raise ValueError(f"Checksum mismatch for {target.name}: expected {checksum}, got {actual}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def archive_members(archive, prefix):
    """Validate every path before extraction and strip the enclosing folder."""
    members = []
    seen = set()
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if (
            "\\" in info.filename
            or path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != prefix
            or stat.S_ISLNK(info.external_attr >> 16)
        ):
            raise ValueError(f"Unsafe or unexpected ZIP entry: {info.filename!r}")
        if info.is_dir():
            continue
        relative = PurePosixPath(*path.parts[1:])
        if not relative.parts or relative.as_posix() == MARKER or relative in seen:
            raise ValueError(f"Unexpected or duplicate ZIP entry: {info.filename!r}")
        seen.add(relative)
        members.append((info, relative))
    if not members:
        raise ValueError("Archive contains no dataset files")
    return members


def is_complete(destination, checksum):
    marker = destination / MARKER
    if not marker.is_file():
        return False
    try:
        manifest = json.loads(marker.read_text())
        return (
            manifest["record"] == RECORD_ID
            and manifest["md5"] == checksum
            and bool(manifest["files"])
            and all(
                (destination / name).is_file()
                and (destination / name).stat().st_size == size
                for name, size in manifest["files"].items()
            )
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def install_archive(archive_path, prefix, destination, checksum):
    """Extract into a temporary directory, publishing only complete datasets."""
    with tempfile.TemporaryDirectory(prefix=".dose-i-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "contents"
        staging.mkdir()
        with ZipFile(archive_path) as archive:
            members = archive_members(archive, prefix)
            for info, relative in members:
                target = staging.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, CHUNK_SIZE)
        manifest = {
            "record": RECORD_ID,
            "md5": checksum,
            "files": {path.as_posix(): info.file_size for info, path in members},
        }
        (staging / MARKER).write_text(json.dumps(manifest, indent=2) + "\n")
        # rmdir refuses to remove a nonempty destination, protecting existing data.
        destination.rmdir()
        staging.rename(destination)


def prepare_data(keep_archives=False):
    data_dir = DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    for _, _, folder, _ in ARCHIVES:
        (data_dir / folder).mkdir(exist_ok=True)
    cache = data_dir / ".downloads"
    cache.mkdir(exist_ok=True)
    for filename, prefix, folder, checksum in ARCHIVES:
        destination = data_dir / folder
        if is_complete(destination, checksum):
            print(f"Already complete: {destination}", flush=True)
            continue
        if any(destination.iterdir()):
            raise ValueError(
                f"{destination} contains files but is not a verified complete download. "
                "Move the existing folder aside, then rerun."
            )
        print(f"Downloading {filename} from DOSE-I v2 ({RECORD_ID})", flush=True)
        archive_path = cache / filename
        download(f"{RECORD_URL}/files/{filename}?download=1", archive_path, checksum)
        print(f"Extracting into {destination}", flush=True)
        install_archive(archive_path, prefix, destination, checksum)
        if not keep_archives:
            archive_path.unlink()
    print(f"Dataset ready: {data_dir}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-archives", action="store_true",
        help="Keep verified ZIPs in data/.downloads/ after extraction")
    args = parser.parse_args()
    print(f"Source: {RECORD_URL}\nData Use Agreement: {RECORD_URL}/files/Data_Use_Agreement.txt",
        flush=True)
    try:
        prepare_data(keep_archives=args.keep_archives)
    except (OSError, ValueError, RuntimeError, EOFError, BadZipFile) as error:
        parser.exit(1, f"Download failed: {error}\nFix the issue and rerun the same command.\n")
    except KeyboardInterrupt:
        print("\nInterrupted. Rerun the same command to continue.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
