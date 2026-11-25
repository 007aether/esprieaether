# Changelog — Atulya-All-File-Converter

All notable changes to Atulya-All-File-Converter are documented here.
Follows [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]
- Camera scan OCR with perspective correction
- Android APK (Buildozer)

### Added
- DOCX/ODT/RTF to PDF and PDF to DOCX/ODT (LibreOffice headless; PDF to DOCX is text-only)
- Audio conversion (MP3, WAV, OGG, FLAC, M4A) via ffmpeg
- Video thumbnail extraction: `convert -i clip.mp4 -o thumb.png`
- Batch conversion progress bar
- macOS `.dmg` build in CI
- Test suite and test CI workflow

### Fixed
- `.csv`/`.tsv` files were detected as plain text and converted incorrectly
- `.wav` files were detected as WebP

---

## [v0.2.0] — 2026-09-15
### Added
- PDF merge, split, compress, and password-protect
- Image convert: PNG ↔ JPG ↔ WebP ↔ BMP ↔ TIFF
- CSV ↔ JSON ↔ Excel (xlsx) conversion
- Scan-to-PDF with Tesseract OCR
- Local WebUI server (`python webui.py`)
- Standalone EXE/MSI builds via GitHub Actions
- Amber gold Cinzel typing SVG header in README

### Changed
- All conversions run fully offline (removed cloud fallback)
- Output path now defaults to same directory as input

---

## [v0.1.0] — 2026-08-01
### Added
- Initial CLI: PDF and image conversion
- 40+ format support declaration
- Basic README and LICENSE
