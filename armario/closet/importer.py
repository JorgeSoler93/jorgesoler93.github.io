"""Importación masiva desde carpeta: `top/camiseta-blanca.png`, `shoes/zapatillas.png`…
La subcarpeta da la categoría y el nombre del archivo da el nombre. El color se calcula de la imagen.
Una sidecar opcional `camiseta-blanca.json` junto al archivo puede fijar cualquier atributo."""
from __future__ import annotations

import json
from pathlib import Path

from .service import Closet

CATEGORY_ALIASES = {
    "top": "top", "tops": "top", "arriba": "top", "camisetas": "top", "camisas": "top", "jerseys": "top",
    "bottom": "bottom", "bottoms": "bottom", "abajo": "bottom", "pantalones": "bottom",
    "dress": "dress", "vestidos": "dress", "vestido": "dress",
    "shoes": "shoes", "calzado": "shoes", "zapatos": "shoes", "zapatillas": "shoes",
    "outerwear": "outerwear", "abrigo": "outerwear", "abrigos": "outerwear", "chaquetas": "outerwear",
    "accessory": "accessory", "accesorio": "accessory", "accesorios": "accessory",
}
EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def import_folder(closet: Closet, root: str | Path) -> tuple[list, list[str]]:
    done, errors = [], []
    for f in sorted(Path(root).rglob("*")):
        if f.suffix.lower() not in EXTS:
            continue
        cat = CATEGORY_ALIASES.get(f.parent.name.lower())
        extra = {}
        side = f.with_suffix(".json")
        try:
            if side.is_file():
                extra = json.loads(side.read_text())
            if cat is None and "category" not in extra:
                raise ValueError(f"'{f.parent.name}' no es una categoría conocida (usa top, bottom, shoes, outerwear, dress, accessory)")
            attrs = {"name": f.stem.replace("-", " ").replace("_", " ").strip().capitalize(), "category": cat, **extra}
            done.append(closet.add_from_photo(f.read_bytes(), attrs=attrs))
        except Exception as e:
            errors.append(f"{f}: {e}")
    return done, errors
