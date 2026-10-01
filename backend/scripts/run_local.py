"""Run the whole TenderLens pipeline locally against a PDF (uses real Bedrock).

    python scripts/run_local.py ../data/samples/gem_9622880.pdf ../data/profiles/acme_infotech.json out.json
"""

import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tenderlens.document import build_document, pdf_pages  # noqa: E402
from tenderlens.pipeline import (  # noqa: E402
    assemble_report, evaluate_extraction, run_eligibility, run_risks, summarize, verify,
)


def main(pdf_path: str, profile_path: str, out_path: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    started = time.monotonic()
    pages = pdf_pages(Path(pdf_path).read_bytes())
    document = build_document(pages)
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    print(f"{len(pages)} pages, {len(document)} chars")

    with ThreadPoolExecutor(max_workers=2) as pool:
        elig_f, risk_f = pool.submit(run_eligibility, document), pool.submit(run_risks, document)
        eligibility, risks = elig_f.result(), risk_f.result()
    print("eligibility", eligibility["meta"], "\nrisks", risks["meta"])

    verified = verify(eligibility, risks, pages)
    evaluation = evaluate_extraction(verified, profile, as_of=date.today())
    summary = summarize(verified, evaluation, profile["name"])
    report = assemble_report(verified=verified, evaluation=evaluation, summary=summary, profile=profile,
                             stats={"pages": len(pages), "seconds": round(time.monotonic() - started, 1)})
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nVERDICT: {report['verdict_text']}  grounding={report['grounding']}  counts={report['counts']}")
    for r in report["results"]:
        print(f"  [{r['status']:<12}] {r['criterion']['description']}  -> {r['reason']}")
    for r in report["risks"]:
        print(f"  risk {r['severity']:<6} {'✓' if r['grounded'] else '✗'} {r['title']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
