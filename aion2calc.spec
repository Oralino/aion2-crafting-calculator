# PyInstaller build for the shared .exe (one-folder). Build: python -m PyInstaller aion2calc.spec
# Output: dist/Aion2CraftingCalculator/Aion2CraftingCalculator.exe (zip the whole folder to share).
import hashlib
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# RapidOCR models the app uses (ocr/market.py): text detection, direction and English
# recognition. Bundled so the first F10 needs no download; the other models are left out.
RAPIDOCR_MODELS = {
    "PP-OCRv6_det_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "en_PP-OCRv5_rec_mobile.onnx",
}
rapidocr_data = [
    (src, dest)
    for src, dest in collect_data_files("rapidocr")
    if not src.endswith(".onnx") or Path(src).name in RAPIDOCR_MODELS
]
missing = RAPIDOCR_MODELS - {Path(src).name for src, _ in rapidocr_data}
if missing:
    raise SystemExit(f"RapidOCR models not downloaded yet: {sorted(missing)}; run the tests once")
# RapidOCR re-checks each model's SHA256 at start and re-downloads a bad one, which fails offline:
# never ship a damaged or half-downloaded model.
known_hashes = next(Path(s) for s, _ in rapidocr_data if s.endswith("default_models.yaml"))
known_hashes_text = known_hashes.read_text(encoding="utf-8")
for src, _ in rapidocr_data:
    if src.endswith(".onnx"):
        digest = hashlib.sha256(Path(src).read_bytes()).hexdigest()
        if digest not in known_hashes_text:
            raise SystemExit(f"{Path(src).name} is damaged (SHA256 mismatch); delete it, run tests")

a = Analysis(
    ["src/aion2calc/app.py"],
    pathex=["src"],
    datas=[
        ("data/recipes.json", "data"),
        *collect_data_files("aion2calc"),  # fonts + OFL licences, digit templates
        *rapidocr_data,
    ],
    hiddenimports=collect_submodules("rapidocr"),
    excludes=["tkinter", "pytest", "mypy", "ruff"],
)
# Large files the app never uses: OpenCV's video I/O, Qt's software OpenGL fallback (widgets
# don't need OpenGL) and Qt's own UI translations (the app is English only).
UNUSED = ("opencv_videoio_ffmpeg", "opengl32sw.dll", "PySide6/translations", "PySide6\\translations")
a.binaries = [b for b in a.binaries if not any(u in b[0] for u in UNUSED)]
a.datas = [d for d in a.datas if not any(u in d[0] for u in UNUSED)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Aion2CraftingCalculator",
    console=False,
    # The game runs as administrator; Windows only passes the F10 hotkey to an app that is too.
    uac_admin=True,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Aion2CraftingCalculator")
