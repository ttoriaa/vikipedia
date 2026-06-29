from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from confluence_api import ConfluenceClient, resolve_confluence_config  # noqa: E402


class ConfluenceDirectClient(ConfluenceClient):
    @classmethod
    def for_instance(cls, instance: str) -> "ConfluenceDirectClient":
        return cls(resolve_confluence_config(instance, strict_instance=True))

