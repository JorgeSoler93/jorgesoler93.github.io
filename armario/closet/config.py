from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _ids(raw: str) -> set[int]:
    return {int(x) for x in raw.replace(" ", "").split(",") if x}


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("./data")
    db_path: Path = Path("./data/armario.db")
    supabase_url: str = ""
    supabase_key: str = ""
    anthropic_key: str = ""
    model: str = "claude-sonnet-5-5"
    telegram_token: str = ""
    telegram_allowed: set[int] = field(default_factory=set)
    api_token: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ
        data_dir = Path(e.get("ARMARIO_DATA_DIR", "./data"))
        return cls(
            data_dir=data_dir,
            db_path=Path(e.get("ARMARIO_DB", str(data_dir / "armario.db"))),
            supabase_url=e.get("SUPABASE_URL", "").rstrip("/"),
            supabase_key=e.get("SUPABASE_SERVICE_KEY", ""),
            anthropic_key=e.get("ANTHROPIC_API_KEY", ""),
            model=e.get("ARMARIO_MODEL", "claude-sonnet-5-5"),
            telegram_token=e.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_allowed=_ids(e.get("TELEGRAM_ALLOWED_IDS", "")),
            api_token=e.get("ARMARIO_API_TOKEN", ""),
        )
