"""Lógica de negocio. Telegram y la web llaman solo a esto."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import imaging, recommender, urlfetch
from .ai import AI
from .config import Settings
from .models import Item, Outfit, now_iso
from .repo import Repo


class NotFound(LookupError):
    pass


class Closet:
    def __init__(self, repo: Repo, ai: AI, data_dir: Path, cleaner: Callable[[bytes], bytes] | None = None):
        self.repo, self.ai, self.cleaner = repo, ai, cleaner
        self.img_dir = Path(data_dir) / "img"
        self.img_dir.mkdir(parents=True, exist_ok=True)

    # -- resolución de ids cortos (los que se ven en Telegram) --
    def _item(self, ref: str) -> Item:
        m = [i for i in self.repo.list_items() if i.id.startswith(ref)]
        if len(m) != 1:
            raise NotFound(f"No encuentro la prenda '{ref}'" if not m else f"'{ref}' es ambiguo")
        return m[0]

    def _outfit(self, ref: str) -> Outfit:
        m = [o for o in self.repo.list_outfits(200) if o.id.startswith(ref)]
        if len(m) != 1:
            raise NotFound(f"No encuentro el conjunto '{ref}'")
        return m[0]

    # -- prendas --
    def add_from_photo(self, data: bytes, comment: str = "", source_url: str = "") -> Item:
        jpg = imaging.normalize(data)
        attrs = self.ai.analyze_image(jpg, "image/jpeg", comment)
        item = Item(**attrs.model_dump(), source_url=source_url)
        (self.img_dir / f"{item.id}.jpg").write_bytes(jpg)
        item.image_file = f"{item.id}.jpg"
        item.clean_file = self._clean(item.id, jpg)
        return self.repo.add_item(item)

    def _clean(self, id_: str, jpg: bytes) -> str:
        """Generativo si hay proveedor; si falla, recorte clásico; si falla, sin recorte."""
        for fn in (self.cleaner, imaging.remove_background):
            if fn is None:
                continue
            try:
                png = fn(jpg)
                imaging.load(png)  # valida que lo devuelto es una imagen
                (self.img_dir / f"{id_}.png").write_bytes(png)
                return f"{id_}.png"
            except Exception:
                continue
        return ""

    def add_from_url(self, url: str, comment: str = "") -> Item:
        data, hint = urlfetch.fetch_image(url)
        return self.add_from_photo(data, " ".join(x for x in (comment, hint) if x), source_url=url)

    def list_items(self, category: str | None = None) -> list[Item]:
        return self.repo.list_items(category)

    def get_item(self, ref: str) -> Item:
        return self._item(ref)

    def update_item(self, ref: str, **fields) -> Item:
        item = self._item(ref)
        allowed = set(Item.model_fields) - {"id", "created_at"}
        clean = {k: v for k, v in fields.items() if k in allowed and v is not None}
        Item.model_validate({**item.model_dump(), **clean})  # valida antes de guardar
        return self.repo.update_item(item.id, **clean)

    def delete_item(self, ref: str) -> Item:
        item = self._item(ref)
        self.repo.delete_item(item.id)
        for f in (item.image_file, item.clean_file):
            if f:
                (self.img_dir / f).unlink(missing_ok=True)
        return item

    def image_path(self, ref: str, clean: bool = True) -> Path:
        item = self._item(ref)
        name = (item.clean_file if clean and item.clean_file else item.image_file)
        return self.img_dir / name

    # -- conjuntos --
    def recommend(self, occasion: str = "", temp_c: float | None = None, comment: str = "", limit: int = 3):
        cands = recommender.recommend(self.repo.list_items(), occasion=occasion, temp_c=temp_c, limit=limit)
        if not cands:
            return []
        ctx = ", ".join(x for x in (occasion, f"{temp_c:g}°C" if temp_c is not None else "", comment) if x)
        payload = [
            {"prendas": [f"{i.name} ({', '.join(i.colors)})" for i in c.items], "motivos": c.reasons} for c in cands
        ]
        try:
            texts = self.ai.explain_outfits(payload, ctx)
        except Exception:
            texts = []
        out = []
        for n, c in enumerate(cands):
            expl = texts[n] if n < len(texts) else "; ".join(c.reasons)
            out.append(self.repo.add_outfit(Outfit(item_ids=[i.id for i in c.items], occasion=occasion, explanation=expl, score=c.score)))
        return out

    def outfit_items(self, outfit: Outfit) -> list[Item]:
        return [i for i in (self.repo.get_item(x) for x in outfit.item_ids) if i]

    def wear(self, ref: str) -> Outfit:
        o, ts = self._outfit(ref), now_iso()
        for it in self.outfit_items(o):
            self.repo.update_item(it.id, wear_count=it.wear_count + 1, last_worn=ts)
        return self.repo.update_outfit(o.id, worn_on=ts)

    def rate(self, ref: str, rating: int) -> Outfit:
        if not 1 <= rating <= 5:
            raise ValueError("La nota va de 1 a 5")
        return self.repo.update_outfit(self._outfit(ref).id, rating=rating)


def build(settings: Settings | None = None, ai: AI | None = None, repo: Repo | None = None) -> Closet:
    from .ai import ClaudeAI
    from .repo import SQLiteRepo, SupabaseRepo

    s = settings or Settings.from_env()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    if repo is None:
        repo = SupabaseRepo(s.supabase_url, s.supabase_key) if s.supabase_url else SQLiteRepo(str(s.db_path))
    from .imagegen import OpenAIImageCleaner

    cleaner = OpenAIImageCleaner(s.openai_key, s.image_model) if s.openai_key else None
    return Closet(repo, ai or ClaudeAI(s.anthropic_key, s.model), s.data_dir, cleaner)
