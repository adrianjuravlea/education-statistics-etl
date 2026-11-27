"""Configure concise CLI and optional run log output."""
import logging
from pathlib import Path

def configure(level: str, path: Path | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)
