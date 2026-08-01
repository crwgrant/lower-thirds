#!/usr/bin/env python3
"""Build a standalone Lower Thirds bundle with PyInstaller."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "lower-thirds.spec"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
RELEASES_DIR = DIST_DIR / "releases"


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def read_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("Could not read version from pyproject.toml")


def clean() -> None:
    for path in (BUILD_DIR, DIST_DIR / "lower-thirds", DIST_DIR / "Lower Thirds.app"):
        if path.exists():
            shutil.rmtree(path)


def bundle_path() -> Path:
    if sys.platform == "darwin":
        return DIST_DIR / "Lower Thirds.app"
    return DIST_DIR / "lower-thirds"


def package_release(version: str) -> Path:
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    machine = platform.machine().lower()
    bundle = bundle_path()

    if not bundle.exists():
        raise FileNotFoundError(f"Expected build output at {bundle}")

    if sys.platform == "darwin":
        stem = RELEASES_DIR / f"lower-thirds-{version}-macos-{machine}"
        archive_format = "zip"
    elif sys.platform == "win32":
        stem = RELEASES_DIR / f"lower-thirds-{version}-windows-{machine}"
        archive_format = "zip"
    else:
        stem = RELEASES_DIR / f"lower-thirds-{version}-linux-{machine}"
        archive_format = "gztar"

    for existing in RELEASES_DIR.glob(f"{stem.name}*"):
        existing.unlink()

    shutil.make_archive(str(stem), archive_format, root_dir=bundle.parent, base_dir=bundle.name)

    suffix = ".zip" if archive_format == "zip" else ".tar.gz"
    return Path(f"{stem}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous PyInstaller output before building",
    )
    parser.add_argument(
        "--no-package",
        action="store_true",
        help="Build the bundle only; skip creating release archive",
    )
    args = parser.parse_args()

    if args.clean:
        clean()

    run([sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"])

    bundle = bundle_path()
    if not bundle.exists():
        print(f"Build finished but bundle not found: {bundle}", file=sys.stderr)
        return 1

    print(f"Built: {bundle}")

    if args.no_package:
        return 0

    version = read_version()
    archive = package_release(version)
    print(f"Release archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
