"""Build the shared Lambda code asset into build/lambda (Linux x86_64 wheels, no Docker needed)."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "lambda"
DEPS = ["anthropic[bedrock]>=1.11", "pydantic>=2.8", "rapidfuzz>=3.9", "pypdf>=5.0"]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--quiet", "--target", str(OUT),
        "--platform", "manylinux2014_x86_64", "--implementation", "cp", "--python-version", "3.12",
        "--only-binary=:all:", "--upgrade", *DEPS,
    ], check=True)

    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "tests")
    for pkg in ("tenderlens", "handlers"):
        shutil.copytree(ROOT / "backend" / pkg, OUT / pkg, ignore=ignore)
    data = OUT / "data"
    shutil.copytree(ROOT / "data" / "profiles", data / "profiles")
    (data / "samples").mkdir(parents=True)
    shutil.copy(ROOT / "data" / "samples" / "samples.json", data / "samples" / "samples.json")
    schemes = ROOT / "data" / "schemes" / "schemes.json"
    if schemes.exists():
        (data / "schemes").mkdir()
        shutil.copy(schemes, data / "schemes" / "schemes.json")

    for p in OUT.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"built {OUT} ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
