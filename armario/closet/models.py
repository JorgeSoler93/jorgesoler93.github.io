from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["top", "bottom", "dress", "shoes", "outerwear", "accessory"]
Status = Literal["clean", "dirty"]

# Paleta cerrada: la IA debe elegir de aquí, así el recomendador puede razonar.
COLORS = [
    "negro", "blanco", "gris", "beige", "marrón", "azul marino", "azul", "celeste",
    "verde", "caqui", "rojo", "burdeos", "rosa", "naranja", "amarillo", "morado",
]
SEASONS = ["primavera", "verano", "otoño", "invierno"]


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ItemAttributes(BaseModel):
    """Lo que la IA extrae de una foto. Todo es corregible por el usuario."""

    name: str = "Prenda"
    category: Category = "top"
    subcategory: str = ""  # camiseta, vaquero, zapatillas...
    colors: list[str] = Field(default_factory=list)
    pattern: str = "liso"
    material: str = ""
    formality: int = Field(2, ge=1, le=5)  # 1 deporte ... 5 etiqueta
    warmth: int = Field(2, ge=1, le=5)  # 1 muy fresco ... 5 muy abrigado
    seasons: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    notes: str = ""


class Item(ItemAttributes):
    id: str = Field(default_factory=new_id)
    image_file: str = ""  # foto original normalizada (jpg)
    clean_file: str = ""  # recorte sin fondo (png)
    source_url: str = ""
    status: Status = "clean"
    wear_count: int = 0
    last_worn: str | None = None
    created_at: str = Field(default_factory=now_iso)


class Outfit(BaseModel):
    id: str = Field(default_factory=new_id)
    item_ids: list[str]
    occasion: str = ""
    explanation: str = ""
    score: float = 0.0
    rating: int | None = None
    worn_on: str | None = None
    created_at: str = Field(default_factory=now_iso)


def short(id_: str) -> str:
    return id_[:6]
