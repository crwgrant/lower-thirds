#!/usr/bin/env python3
"""Render assets/icon.svg into PNG, ICO, and ICNS bundles."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QImageWriter, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "icon.svg"

PNG_SIZES = (16, 32, 64, 128, 256, 512, 1024)
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def render_svg(size: int) -> QImage:
    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise RuntimeError(f"Could not load SVG: {SVG_PATH}")

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    return image


def save_png(image: QImage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(path), "PNG"):
        raise RuntimeError(f"Failed to write {path}")


def save_ico(images: dict[int, QImage], path: Path) -> None:
    writer = QImageWriter(str(path), b"ico")
    if not writer.write(images[max(ICO_SIZES)]):
        raise RuntimeError(f"Failed to write {path}")


def save_icns(images: dict[int, QImage], path: Path) -> None:
    writer = QImageWriter(str(path), b"icns")
    if not writer.write(images[1024]):
        raise RuntimeError(f"Failed to write {path}")


def save_icns_via_iconutil(images: dict[int, QImage], path: Path) -> None:
    iconset = ASSETS / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()

    iconset_entries = (
        (16, 16, 32),
        (32, 32, 64),
        (128, 128, 256),
        (256, 256, 512),
        (512, 512, 1024),
    )
    for base, one_x, two_x in iconset_entries:
        save_png(images[one_x], iconset / f"icon_{base}x{base}.png")
        save_png(images[two_x], iconset / f"icon_{base}x{base}@2x.png")

    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(path)], check=True)
    shutil.rmtree(iconset)


def main() -> int:
    if not SVG_PATH.exists():
        print(f"Missing source icon: {SVG_PATH}", file=sys.stderr)
        return 1

    app = QApplication([])
    images = {size: render_svg(size) for size in PNG_SIZES}

    save_png(images[1024], ASSETS / "icon.png")

    icons_dir = ASSETS / "icons"
    for size, image in images.items():
        save_png(image, icons_dir / f"icon_{size}x{size}.png")

    save_ico({size: images[size] for size in ICO_SIZES if size in images}, ASSETS / "icon.ico")

    if sys.platform == "darwin":
        save_icns_via_iconutil(images, ASSETS / "icon.icns")
    else:
        save_icns(images, ASSETS / "icon.icns")

    print(f"Generated icons in {ASSETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
