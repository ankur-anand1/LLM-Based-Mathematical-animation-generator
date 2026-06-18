"""Download the ManimBench dataset (417 description->code pairs) for RAG/fine-tuning.

Saves to data/manimbench.json as a list of {"description": ..., "code": ...}.

Usage:
    python download_manimbench.py

Needs internet. Tries the `datasets` library; if missing, tells you how to install.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
OUT = DATA_DIR / "manimbench.json"

REPO = "SuienR/ManimBench-v1"
PARQUET = "manim_sft_dataset_all.parquet"


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    try:
        from huggingface_hub import hf_hub_download
        import pandas as pd
    except ImportError:
        print("Missing libraries. Install them with:")
        print("    .venv\\Scripts\\python.exe -m pip install huggingface_hub pandas pyarrow")
        return 1

    print(f"Downloading {REPO}/{PARQUET} ...")
    try:
        path = hf_hub_download(REPO, PARQUET, repo_type="dataset")
        df = pd.read_parquet(path)
    except Exception as e:  # noqa: BLE001
        print(f"Download failed: {e}")
        return 1

    # Prefer the human-reviewed description; fall back to the generated one.
    desc_col = "Reviewed Description" if "Reviewed Description" in df.columns else "Generated Description"
    items: list[dict] = []
    for _, row in df.iterrows():
        desc = str(row.get(desc_col, "") or "").strip()
        code = str(row.get("Code", "") or "").strip()
        if desc and code:
            items.append({"description": desc, "code": code})

    OUT.write_text(json.dumps(items, indent=2), encoding="utf-8")
    print(f"Saved {len(items)} examples to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
