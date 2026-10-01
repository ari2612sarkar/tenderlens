"""Download official scheme sources into data/schemes/sources/<id>.json as page-numbered text."""

import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tenderlens.document import clean_text, pdf_pages  # noqa: E402

OUT = ROOT / "data" / "schemes" / "sources"

CATALOG = [
    {"id": "ppp-mse", "name": "Public Procurement Policy for Micro & Small Enterprises",
     "ministry": "Ministry of MSME",
     "source_url": "https://www.dcmsme.gov.in/FAQs-PPP_25032022.pdf"},
    {"id": "cgtmse", "name": "Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
     "ministry": "Ministry of MSME and SIDBI", "source_url": "https://www.cgtmse.in/Home/VS/95"},
    {"id": "pmegp", "name": "Prime Minister's Employment Generation Programme (PMEGP)",
     "ministry": "Ministry of MSME (KVIC)",
     "source_url": "https://www.kvic.gov.in/kvicres/update/pmegp/New%20PMEGP%20guidelines.pdf"},
    {"id": "zed", "name": "MSME Sustainable (ZED) Certification Scheme", "ministry": "Ministry of MSME",
     "source_url": "https://zed.msme.gov.in/subsidy-on-cost-of-certification"},
    {"id": "standup-india", "name": "Stand-Up India", "ministry": "Department of Financial Services",
     "source_url": "https://www.standupmitra.in/Home/SUISchemes"},
    {"id": "sisfs", "name": "Startup India Seed Fund Scheme", "ministry": "DPIIT, Ministry of Commerce and Industry",
     "source_url": "https://www.startupindia.gov.in/content/dam/invest-india/Templates/public/"
                   "Guidelines%20for%20Startup%20India%20Seed%20Fund%20Scheme.pdf"},
]


def html_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style|noscript|svg|head|nav|footer)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|td|th)>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    return clean_text("\n".join(line for line in lines if line))


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for scheme in CATALOG:
        try:
            raw = fetch(scheme["source_url"])
        except Exception as err:  # noqa: BLE001
            print(f"FAILED {scheme['id']}: {err}")
            continue
        pages = pdf_pages(raw) if raw[:4] == b"%PDF" else {1: html_text(raw)}
        (OUT / f"{scheme['id']}.json").write_text(json.dumps({**scheme, "pages": pages}, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
        print(f"{scheme['id']}: {len(pages)} pages, {sum(len(t) for t in pages.values())} chars")


if __name__ == "__main__":
    main()
