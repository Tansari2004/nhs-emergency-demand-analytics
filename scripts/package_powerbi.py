"""Bundle the complete editable NHS source preview with integrity hashes."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi/upgrade"


def main():
    (OUT / "tools").mkdir(exist_ok=True)
    (OUT / "data").mkdir(exist_ok=True)
    for name in ("build_powerbi_model.py", "build_powerbi_report.py", "verify_powerbi.py", "verify_powerquery.cjs"):
        shutil.copyfile(ROOT / "scripts" / name, OUT / "tools" / name)
    for file in (ROOT / "powerbi/data").glob("*.csv"):
        shutil.copyfile(file, OUT / "data" / file.name)
    shutil.copyfile(ROOT / "requirements-repro.txt", OUT / "requirements-repro.txt")
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "manifest.json"
                   and ".pbi" not in p.parts and "__pycache__" not in p.parts)
    manifest = {"format": "Editable NHS PBIP source preview", "native_runtime_verified": False,
                "workspace_updated": False,
                "files": {p.relative_to(OUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = ROOT / "powerbi/NHS_Analytics_Source_Preview.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for file in files + [OUT / "manifest.json"]:
            bundle.write(file, "NHS_Analytics_Source_Preview/" + file.relative_to(OUT).as_posix())
    print(json.dumps({"archive": str(archive.relative_to(ROOT)), "bytes": archive.stat().st_size}))


if __name__ == "__main__":main()
