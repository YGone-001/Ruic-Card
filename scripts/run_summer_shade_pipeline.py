"""Run the RuiC-card pipeline for the fourth card using Blender's mirror."""

from __future__ import annotations

import os
import runpy
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL = Path.home() / ".agents" / "skills" / "RuiC-card-skill"
SKILL_ROOT = Path(
    os.environ.get(
        "RUIC_CARD_SKILL",
        DEFAULT_SKILL if (DEFAULT_SKILL / "scripts" / "run_pipeline.py").is_file()
        else Path.home() / ".codex" / "skills" / "ruic-card-skill",
    )
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
argv = [
    str(SCRIPTS / "run_pipeline.py"),
    "--project",
    str(ROOT / "cards" / "summer-shade"),
]
# The portable Blender lives in the shared repository tools/ directory, not
# inside a card, so every card reuses one verified install.
shared = sorted((ROOT / "tools").glob("blender-*/blender.exe"))
if shared and "--blender" not in argv:
    argv += ["--blender", str(shared[0])]
sys.argv = argv
runpy.run_path(str(SCRIPTS / "run_pipeline.py"), run_name="__main__")
