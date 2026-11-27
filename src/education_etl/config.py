"""Read project configuration and controlled territorial identifiers."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Settings:
    territories: dict[str, dict[str, str]]
    classification_path: Path
    exhaustive_parents: tuple[str, ...]

def load_settings(path: Path = ROOT / "config" / "etl_config.json") -> Settings:
    content = json.loads(path.read_text(encoding="utf-8"))
    with (path.parent / content["territories"]).open(encoding="utf-8", newline="") as stream:
        territories = {row["territory_name_original"]: row for row in csv.DictReader(stream)}
    return Settings(territories, path.parent / content["classification"], tuple(content["exhaustive_parents"]))
