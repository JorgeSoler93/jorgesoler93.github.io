"""Generador de conjuntos: combinatoria + reglas puntuadas. La IA solo explica después."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .models import Item

NEUTRALS = {"negro", "blanco", "gris", "beige", "marrón", "azul marino", "caqui"}
# pares de colores vivos que combinan bien
GOOD_PAIRS = {
    frozenset(p)
    for p in [
        ("azul", "naranja"), ("azul", "amarillo"), ("celeste", "rosa"), ("verde", "burdeos"),
        ("rojo", "azul"), ("morado", "amarillo"), ("celeste", "burdeos"), ("rosa", "verde"),
    ]
}
OCCASIONS = {  # formalidad objetivo
    "deporte": 1, "casual": 2, "diario": 2, "paseo": 2, "universidad": 2, "trabajo": 3, "oficina": 3,
    "cita": 3, "cena": 3, "fiesta": 3, "reunión": 4, "boda": 5, "formal": 5, "evento": 4,
}
PER_CATEGORY = 12  # límite de candidatos por categoría para acotar la combinatoria


@dataclass
class Candidate:
    items: list[Item]
    score: float
    reasons: list[str] = field(default_factory=list)


def target_formality(occasion: str) -> int | None:
    occ = occasion.lower()
    for key, val in OCCASIONS.items():
        if key in occ:
            return val
    return None


def target_warmth(temp_c: float) -> float:
    return 1 if temp_c >= 26 else 2 if temp_c >= 20 else 3 if temp_c >= 14 else 4 if temp_c >= 8 else 5


def color_score(items: list[Item]) -> tuple[float, str]:
    vivid = {c for it in items for c in it.colors if c not in NEUTRALS}
    if len(vivid) <= 1:
        return 1.0, "colores equilibrados"
    if len(vivid) == 2 and frozenset(vivid) in GOOD_PAIRS:
        return 0.7, "contraste de colores que funciona"
    return -1.0 * (len(vivid) - 1), "demasiados colores vivos"


def _days_since(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 86400


def _outfit_warmth(core: list[Item]) -> float:
    """Capa base (arriba+abajo o vestido) + aporte de la prenda de abrigo. El calzado no cuenta."""
    base = [i.warmth for i in core if i.category in ("top", "bottom", "dress")] or [2]
    jacket = [i.warmth for i in core if i.category == "outerwear"]
    return sum(base) / len(base) + sum((j - 1) * 0.4 for j in jacket)


def score_outfit(items: list[Item], *, formality: int | None, temp_c: float | None, now: datetime) -> Candidate:
    score, reasons = 0.0, []
    cs, why = color_score(items)
    score += cs * 1.5
    reasons.append(why)

    core = [i for i in items if i.category != "accessory"]
    f = [i.formality for i in core]
    score -= (max(f) - min(f)) * 0.8  # que no mezcle chándal con americana
    if formality is not None:
        diff = abs(sum(f) / len(f) - formality)
        score -= diff * 1.5
        reasons.append("nivel de formalidad adecuado" if diff <= 0.7 else "formalidad algo desajustada")

    if temp_c is not None:
        w = _outfit_warmth(core)
        diff = abs(w - target_warmth(temp_c))
        score -= diff * 1.2
        reasons.append(f"abrigo adecuado para {temp_c:g}°C" if diff <= 0.8 else f"abrigo poco ideal para {temp_c:g}°C")

    for it in items:
        d = _days_since(it.last_worn, now)
        if d is not None and d < 3:
            score -= 1.5 if it.category in ("top", "dress") else 0.4  # vaqueros y zapatos sí se repiten
            reasons.append(f"{it.name} se usó hace poco")
        score -= 0.05 * it.wear_count
    return Candidate(items, round(score, 2), reasons)


def _pool(items: list[Item], category: str) -> list[Item]:
    pool = [i for i in items if i.category == category and i.status == "clean"]
    pool.sort(key=lambda i: (i.wear_count, i.last_worn or ""))  # prioriza lo menos usado
    return pool[:PER_CATEGORY]


def recommend(
    items: list[Item], *, occasion: str = "", temp_c: float | None = None, limit: int = 3, now: datetime | None = None
) -> list[Candidate]:
    now = now or datetime.now(timezone.utc)
    formality = target_formality(occasion)
    tops, bottoms, dresses = _pool(items, "top"), _pool(items, "bottom"), _pool(items, "dress")
    shoes, outer = _pool(items, "shoes"), _pool(items, "outerwear")
    outer_opts: list[Item | None] = [None, *outer]
    shoe_opts: list[Item | None] = shoes or [None]

    bases = [(t, b) for t, b in itertools.product(tops, bottoms)] + [(d,) for d in dresses]
    cands: list[Candidate] = []
    for base, shoe, jacket in itertools.product(bases, shoe_opts, outer_opts):
        combo = [*base, *([shoe] if shoe else []), *([jacket] if jacket else [])]
        cands.append(score_outfit(combo, formality=formality, temp_c=temp_c, now=now))
    cands.sort(key=lambda c: c.score, reverse=True)

    picked: list[Candidate] = []
    for c in cands:  # variedad: no repetir la misma base
        base_ids = {i.id for i in c.items if i.category in ("top", "bottom", "dress")}
        if all(base_ids != {i.id for i in p.items if i.category in ("top", "bottom", "dress")} for p in picked):
            picked.append(c)
        if len(picked) == limit:
            break
    return picked
