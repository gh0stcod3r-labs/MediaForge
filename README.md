# MediaForge Organizer

A local-first desktop app for organizing and renaming video libraries — anime, TV shows, movies, sports, clips, and creator footage — built with [PySide6](https://doc.qt.io/qtforpython/).

MediaForge scans a folder of video files, matches each one against metadata (either fully offline via filename parsing, or online via TMDB / AniList / MyAnimeList / TVMaze), and builds a safe, previewable plan to copy or move everything into a clean, consistently named folder structure.

## Features

- **Metadata matching** — Offline filename parsing by default, with optional online providers (TMDB, AniList, MyAnimeList, TVMaze) for richer, more accurate matches. Provider matching runs on a background thread so the UI never blocks.
- **Safety first** — Copies files by default and never deletes originals; move mode is opt-in. A dry-run mode lets you preview every change before anything touches disk.
- **Duplicate-safe** — Automatically renames on filename conflicts at the destination instead of silently overwriting.
- **Operation & undo log** — Every copy/move/rename is logged; the last batch can be undone in one click, with an optional confirmation prompt.
- **Match confidence & review** — Each match shows its source provider and confidence score, and anything uncertain is flagged as "Needs Review" instead of being silently misfiled.
- **Export** — Operation history can be exported to CSV or JSON for auditing.
- **Light & dark themes**, with the choice persisted between sessions.

## Folder structure produced

```
Anime/Title/S01/Title - S01E01 - Episode Name.ext
TV Shows/Title/S01/Title - S01E01 - Episode Name.ext
Movies/Title (Year)/Title (Year).ext
Sports/League/Year/Event Name - Date.ext
Clips/Project Name/Clip Name.ext
Creator Footage/Project Name/Raw/Clip Name.ext
Other/Title.ext
```

## Installation

```bash
git clone https://github.com/<your-username>/mediaforge-organizer.git
cd mediaforge-organizer
pip install -r requirements.txt
python src/main.py
```

Requires Python 3.10+ and PySide6. No internet connection or paid API keys are required — the offline provider works entirely from local filename parsing.

## Usage

1. Select a **Source Folder** to scan and an **Output Folder** to organize into.
2. Pick a metadata **Provider** (Automatic/Offline by default; add an API key for TMDB, AniList, MyAnimeList, or TVMaze via the "API Key" button if you want online lookups).
3. Choose the **Category** (Anime, TV Show, Movie, Sports, Clips, Creator Footage, Other).
4. Click **Scan Videos** to build a plan — review the proposed filenames, providers, and confidence scores in the table.
5. Enable **Dry Run** to preview without writing anything, or leave **Copy Mode** on to organize non-destructively.
6. Click **Rename & Copy** to execute the plan. Use **Undo Last** to revert the most recent batch if needed.

## Optional: online metadata providers

Online providers are entirely optional — MediaForge works offline out of the box. To enable one:

1. Select it from the **Provider** dropdown.
2. Click **API Key** and paste in your key (TMDB, AniList, MyAnimeList, and TVMaze all offer free API access).

Keys are stored locally in `~/.mediaforge/settings.json` and are never transmitted anywhere except directly to that provider's API.

## Project structure

```
mediaforge-organizer/
├── src/
│   ├── main.py                    # Application entry point
│   └── mediaforge/
│       ├── app.py                 # PySide6 UI (main window)
│       ├── constants.py           # Design tokens & QSS theme generator
│       ├── config.py              # Persisted settings (paths, theme, API keys)
│       ├── scanner.py             # Video file discovery
│       ├── parser.py              # Lightweight filename parsing
│       ├── matcher.py             # Advanced filename → metadata matching
│       ├── async_matcher.py       # Background/parallel provider matching
│       ├── rename_engine.py       # Builds and executes the organization plan
│       ├── logger.py              # Operation log, CSV/JSON export, undo
│       ├── cache.py                # Metadata lookup cache
│       ├── match_report.py        # Per-run match summary/statistics
│       ├── match_result.py        # MatchResult / MatchProvider data model
│       ├── models.py              # MediaType / VideoFile data models
│       ├── operation_result.py    # Result type for copy/move operations
│       ├── error_handler.py       # Central exception → user-facing message mapping
│       ├── dialogs.py             # API key, progress, and confirmation dialogs
│       ├── workers.py             # QThread workers for matching & file operations
│       └── providers/             # Metadata providers (TMDB, AniList, MAL, TVMaze, offline)
├── tests/
│   └── test_rename_engine.py
├── MediaForge.spec                # PyInstaller build spec
└── requirements.txt
```

## Running tests

```bash
pip install pytest
PYTHONPATH=src pytest tests/
```

## Building a standalone executable

A [PyInstaller](https://pyinstaller.org/) spec is included. On the platform you want to target (PyInstaller builds for the OS it runs on):

```bash
pip install pyinstaller
pyinstaller MediaForge.spec
```

The resulting executable is written to `dist/` — `MediaForge.exe` on Windows, `MediaForge` on Linux/macOS.

Alternatively, a GitHub Actions workflow (`.github/workflows/build-windows.yml`) builds the Windows `.exe` automatically: every push to `main` produces a downloadable artifact under the repo's **Actions** tab, and pushing a version tag (e.g. `v0.1.0`) attaches the `.exe` to a GitHub Release.

## Contributing

Issues and pull requests are welcome. Please run the test suite before submitting a PR.

## License

Released under the [MIT License](LICENSE).
