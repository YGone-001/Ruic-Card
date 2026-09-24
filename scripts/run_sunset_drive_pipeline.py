"""Run the skill pipeline with an HTTP user agent accepted by Blender's mirror."""

from __future__ import annotations

import os
import runpy
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(
    os.environ.get("RUIC_CARD_SKILL", Path.home() / ".codex" / "skills" / "ruic-card-skill")
).expanduser()
SCRIPTS = SKILL_ROOT / "scripts"
if not (SCRIPTS / "run_pipeline.py").is_file():
    raise FileNotFoundError(
        f"RuiC Card Skill not found at {SKILL_ROOT}. "
        "Set RUIC_CARD_SKILL to the skill directory."
    )
os.environ["RUIC_BLENDER_BASE"] = "https://mirror.blender.org/release/Blender4.5"
opener = urllib.request.build_opener()
opener.addheaders = [("User-Agent", "Mozilla/5.0 Holo-Card-Studio/1.0")]
urllib.request.install_opener(opener)
sys.path.insert(0, str(SCRIPTS))
sys.argv = [
    str(SCRIPTS / "run_pipeline.py"),
    "--project",
    str(ROOT / "cards" / "sunset-drive"),
    "--skip-npm",
]
runpy.run_path(str(SCRIPTS / "run_pipeline.py"), run_name="__main__")
