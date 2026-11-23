from collections import Counter
from pathlib import Path


def test_supabase_migration_versions_are_unique():
    directory = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
    versions = Counter(path.name.split("_", 1)[0] for path in directory.glob("*.sql"))
    duplicates = sorted(version for version, count in versions.items() if count > 1)
    assert not duplicates, f"Duplicate Supabase migration versions: {', '.join(duplicates)}"
