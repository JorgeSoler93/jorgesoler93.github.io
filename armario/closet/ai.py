"""Capa de IA. `AI` es un protocolo: Claude en producción, `FakeAI` en tests."""
from __future__ import annotations

import base64
import json
from typing import Protocol

from .models import COLORS, SEASONS, ItemAttributes


class AI(Protocol):
    def analyze_image(self, image: bytes, media_type: str, comment: str = "") -> ItemAttributes: ...
    def explain_outfits(self, outfits: list[dict], context: str) -> list[str]: ...


def extract_json(text: str) -> dict | list:
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError("La IA no devolvió JSON")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


def normalize_colors(colors: list[str]) -> list[str]:
    out = []
    for c in colors:
        c = c.strip().lower()
        if c and c not in out:
            out.append(c)
    return out


ANALYZE_SYSTEM = f"""Eres el estilista de un armario personal. Recibes la foto de UNA prenda (o un enlace/foto de tienda)
y un comentario opcional del usuario. Responde SOLO con un objeto JSON con estas claves:
name (corto, p.ej. "Camiseta blanca de algodón"), category (top|bottom|dress|shoes|outerwear|accessory),
subcategory (camiseta, camisa, jersey, vaquero, chino, zapatillas, chaqueta...), colors (lista, elige de: {", ".join(COLORS)}),
pattern (liso, rayas, cuadros, estampado...), material (si se intuye, si no ""), formality (1 deporte .. 5 etiqueta),
warmth (1 muy fresco .. 5 muy abrigado), seasons (subconjunto de: {", ".join(SEASONS)}), style_tags (2-4 palabras: casual, smart, urbano...),
notes (lo útil del comentario del usuario: talla, ocasión, defectos; si no hay, "").
El comentario del usuario manda sobre lo que parezca en la foto."""

EXPLAIN_SYSTEM = """Eres un estilista cercano y directo. Recibes conjuntos ya combinados por un algoritmo (no los cambies)
y el contexto (ocasión, temperatura, comentario). Para cada conjunto, escribe UNA frase en español (máx. 25 palabras)
explicando por qué funciona o cómo llevarlo. Responde SOLO con una lista JSON de strings, en el mismo orden."""


class ClaudeAI:
    def __init__(self, api_key: str, model: str = "claude-sonnet-5-5", client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        self._client, self._model = client, model

    def _text(self, **kw) -> str:
        msg = self._client.messages.create(model=self._model, max_tokens=1024, **kw)
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    def analyze_image(self, image: bytes, media_type: str, comment: str = "") -> ItemAttributes:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(image).decode()}},
            {"type": "text", "text": f"Comentario del usuario: {comment or '(ninguno)'}"},
        ]
        data = extract_json(self._text(system=ANALYZE_SYSTEM, messages=[{"role": "user", "content": content}]))
        attrs = ItemAttributes.model_validate(data)
        attrs.colors = normalize_colors(attrs.colors)
        return attrs

    def explain_outfits(self, outfits: list[dict], context: str) -> list[str]:
        prompt = f"Contexto: {context or 'sin contexto'}\nConjuntos: {json.dumps(outfits, ensure_ascii=False)}"
        data = extract_json(self._text(system=EXPLAIN_SYSTEM, messages=[{"role": "user", "content": prompt}]))
        return [str(x) for x in data][: len(outfits)]


class FakeAI:
    """Determinista, para tests y para probar sin API key."""

    def __init__(self, attrs: ItemAttributes | None = None):
        self.attrs = attrs or ItemAttributes(name="Prenda de prueba", colors=["azul"])
        self.calls: list[str] = []

    def analyze_image(self, image: bytes, media_type: str, comment: str = "") -> ItemAttributes:
        self.calls.append(comment)
        return self.attrs.model_copy(update={"notes": comment})

    def explain_outfits(self, outfits: list[dict], context: str) -> list[str]:
        return [f"Conjunto {i + 1}" for i in range(len(outfits))]
