"""Turn official scheme sources into grounded, typed eligibility rules: data/schemes/schemes.json.

Uses the same agent + grounding check as tenders. Run after fetch_schemes.py (needs Bedrock access).
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tenderlens.agents.llm import structured  # noqa: E402
from tenderlens.agents.prompts import SCHEME_SYSTEM  # noqa: E402
from tenderlens.agents.schemas import SchemeOut, to_criteria  # noqa: E402
from tenderlens.document import build_document  # noqa: E402
from tenderlens.grounding import ground_items  # noqa: E402

SOURCES = ROOT / "data" / "schemes" / "sources"
OUT = ROOT / "data" / "schemes" / "schemes.json"


def ingest(path: Path) -> dict:
    src = json.loads(path.read_text(encoding="utf-8"))
    pages = {int(k): v for k, v in src["pages"].items()}
    out, meta = structured(SCHEME_SYSTEM, f"<scheme_document>\n{build_document(pages)}\n</scheme_document>\n\n"
                           "Extract the scheme's benefit and its eligibility criteria for an enterprise.", SchemeOut)
    criteria = ground_items([c.model_dump() for c in to_criteria(out.criteria)], pages)
    grounded = sum(c["grounded"] for c in criteria)
    print(f"{src['id']}: {len(criteria)} criteria, {grounded} grounded ({meta['seconds']}s)")
    return {"id": src["id"], "name": src["name"], "ministry": src["ministry"], "source_url": src["source_url"],
            "benefit": out.benefit, "criteria": criteria}


def main() -> None:
    paths = sorted(SOURCES.glob("*.json"))
    with ThreadPoolExecutor(max_workers=3) as pool:
        schemes = list(pool.map(ingest, paths))
    OUT.write_text(json.dumps(schemes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
