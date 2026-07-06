"""Tests for the RenameEngine module."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mediaforge.match_result import MatchResult, MatchProvider
from src.mediaforge.rename_engine import RenameEngine
from src.mediaforge.models import MediaType


def test_plan_generation_anime():
    """Test plan generation for anime media type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        matches = []
        for episode in range(1, 6):
            source_file = tmpdir / "source" / f"Beast Tamer - S01E{episode:02d}.mkv"
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.touch()
            matches.append(
                MatchResult(
                    source_path=source_file,
                    filename=source_file.name,
                    provider=MatchProvider.TMDB,
                    confidence=0.95,
                    title="Beast Tamer",
                    series_name="Beast Tamer",
                    season=1,
                    episode=episode,
                    episode_title="Meeting of Fate" if episode == 1 else None,
                )
            )

        engine = RenameEngine()
        dest_root = tmpdir / "output"

        plan = engine.plan_operations(
            matches=matches,
            media_type=MediaType.ANIME,
            destination_root=dest_root,
            operation_type="rename_copy",
        )

        print("[PASS] Anime plan generation:")
        print(f"  Operations: {len(plan.operations)}")
        print(f"  Folders to create: {len(plan.folders_to_create)}")

        op = plan.operations[0]
        print(f"  Destination: {op.destination_path}")

        assert "Beast Tamer" in str(op.destination_path)
        assert "Season 01" in str(op.destination_path)
        assert "Anime" not in str(op.destination_path)
        assert "Meeting of Fate" in str(op.destination_path.name)
        print("  [OK] Correct Series/Season folder structure")


def test_plan_generation_tv():
    """Test plan generation for TV show media type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "source" / "Breaking Bad - S01E01.mkv"
        source_file.parent.mkdir()
        source_file.touch()
        
        match = MatchResult(
            source_path=source_file,
            filename=source_file.name,
            provider=MatchProvider.OFFLINE,
            confidence=0.90,
            title="Breaking Bad",
            season=1,
            episode=1,
        )
        
        engine = RenameEngine()
        dest_root = tmpdir / "output"
        
        plan = engine.plan_operations(
            matches=[match],
            media_type=MediaType.TV_SHOW,
            destination_root=dest_root,
            operation_type="rename_copy",
        )
        
        print("\n[PASS] TV Show plan generation:")
        op = plan.operations[0]
        print(f"  Destination: {op.destination_path}")
        
        assert "Breaking Bad" in str(op.destination_path)
        assert "Season 01" in str(op.destination_path)
        assert "TV Shows" not in str(op.destination_path)
        print("  [OK] Correct TV show structure")


def test_plan_generation_movie():
    """Test plan generation for movie media type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "source" / "Inception.mkv"
        source_file.parent.mkdir()
        source_file.touch()
        
        match = MatchResult(
            source_path=source_file,
            filename=source_file.name,
            provider=MatchProvider.OFFLINE,
            confidence=0.95,
            title="Inception",
            year=2010,
        )
        
        engine = RenameEngine()
        dest_root = tmpdir / "output"
        
        plan = engine.plan_operations(
            matches=[match],
            media_type=MediaType.MOVIE,
            destination_root=dest_root,
            operation_type="rename_copy",
        )
        
        print("\n[PASS] Movie plan generation:")
        op = plan.operations[0]
        print(f"  Destination: {op.destination_path}")
        
        assert "Movies" not in str(op.destination_path)
        assert "Inception" in str(op.destination_path)
        assert "2010" in str(op.destination_path.name)
        print("  [OK] Correct movie structure with year")


def test_dry_run():
    """Test dry run (no files created)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "source" / "test.mkv"
        source_file.parent.mkdir()
        source_file.write_text("dummy")
        
        match = MatchResult(
            source_path=source_file,
            filename=source_file.name,
            provider=MatchProvider.OFFLINE,
            confidence=0.95,
            title="Test",
        )
        
        engine = RenameEngine()
        dest_root = tmpdir / "output"
        
        plan = engine.plan_operations(
            matches=[match],
            media_type=MediaType.OTHER,
            destination_root=dest_root,
            operation_type="rename_copy",
            is_dry_run=True,
        )
        
        result = engine.execute_plan(plan)
        
        print("\n[PASS] Dry run test:")
        print(f"  Files skipped: {len(result.skipped)}")
        print(f"  Output folder created: {dest_root.exists()}")
        
        assert len(result.skipped) == 1
        assert not dest_root.exists()
        print("  [OK] Dry run made no changes")


def test_batch_with_failures():
    """Test batch operation continues after failures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Valid file
        source1 = tmpdir / "source" / "valid.mkv"
        source1.parent.mkdir()
        source1.write_text("dummy")
        
        # Missing file
        source2 = Path(tmpdir / "source" / "missing.mkv")
        
        matches = [
            MatchResult(
                source_path=source1,
                filename=source1.name,
                provider=MatchProvider.OFFLINE,
                confidence=0.95,
                title="Valid",
            ),
            MatchResult(
                source_path=source2,
                filename=source2.name,
                provider=MatchProvider.OFFLINE,
                confidence=0.95,
                title="Missing",
            ),
        ]
        
        engine = RenameEngine()
        dest_root = tmpdir / "output"
        
        plan = engine.plan_operations(
            matches=matches,
            media_type=MediaType.OTHER,
            destination_root=dest_root,
            operation_type="rename_copy",
        )
        
        result = engine.execute_plan(plan)
        
        print("\n[PASS] Batch error recovery test:")
        print(f"  Successful: {len(result.successful)}")
        print(f"  Failed: {len(result.failed)}")
        
        # Should continue after first failure
        assert len(result.successful) + len(result.failed) == 2
        assert len(result.failed) >= 1
        print("  [OK] Batch continued after failure")


def test_beast_tamer_folder_normalization():
    """Ensure polluted series names do not create per-episode folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        engine = RenameEngine()
        dest_root = tmpdir / "fixed"
        inputs = [
            ("Beast Tamer ] Episode 01 - S01E01 - Meeting of Fate.mkv", 1, "Meeting of Fate"),
            ("Beast Tamer ] Episode 02 - S01E02 - Comrades.mkv", 2, "Comrades"),
            ("Beast Tamer ] Episode 03 - S01E03 - Another Ultimate Species.mkv", 3, "Another Ultimate Species"),
        ]

        matches = []
        for filename, episode, episode_title in inputs:
            source_file = tmpdir / "source" / filename
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.touch()
            matches.append(
                MatchResult(
                    source_path=source_file,
                    filename=filename,
                    provider=MatchProvider.OFFLINE,
                    confidence=0.90,
                    title=filename.replace(".mkv", ""),
                    series_name=filename.replace(".mkv", ""),
                    season=1,
                    episode=episode,
                    episode_title=episode_title,
                )
            )

        plan = engine.plan_operations(
            matches=matches,
            media_type=MediaType.ANIME,
            destination_root=dest_root,
            operation_type="rename_copy",
        )

        folders = {str(op.destination_path.parent) for op in plan.operations}
        assert folders == {str(dest_root / "Beast Tamer" / "Season 01")}
        expected_names = {
            "Beast Tamer - S01E01 - Meeting of Fate.mkv",
            "Beast Tamer - S01E02 - Comrades.mkv",
            "Beast Tamer - S01E03 - Another Ultimate Species.mkv",
        }
        assert {op.destination_path.name for op in plan.operations} == expected_names
        print("\n[PASS] Beast Tamer normalization test")


def test_monster_musume_numbered_files():
    """Ensure numbered anime files map to one series/season folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        engine = RenameEngine()
        dest_root = tmpdir / "fixed"
        matches = []
        for episode in [1, 2]:
            filename = f"Monster Musume no Oishasan - {episode:02d}.mkv"
            source_file = tmpdir / "source" / filename
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.touch()
            matches.append(
                MatchResult(
                    source_path=source_file,
                    filename=filename,
                    provider=MatchProvider.OFFLINE,
                    confidence=0.85,
                    title=filename.replace(".mkv", ""),
                    series_name=filename.replace(".mkv", ""),
                    season=1,
                    episode=episode,
                )
            )

        plan = engine.plan_operations(
            matches=matches,
            media_type=MediaType.ANIME,
            destination_root=dest_root,
            operation_type="rename_copy",
        )

        folders = {str(op.destination_path.parent) for op in plan.operations}
        assert folders == {str(dest_root / "Monster Musume No Oishasan" / "Season 01")}
        expected_names = {
            "Monster Musume No Oishasan - S01E01.mkv",
            "Monster Musume No Oishasan - S01E02.mkv",
        }
        assert {op.destination_path.name for op in plan.operations} == expected_names
        print("[PASS] Monster Musume normalization test")


if __name__ == "__main__":
    test_plan_generation_anime()
    test_plan_generation_tv()
    test_plan_generation_movie()
    test_dry_run()
    test_batch_with_failures()
    test_beast_tamer_folder_normalization()
    test_monster_musume_numbered_files()
    print("\n[SUCCESS] All tests passed!")
