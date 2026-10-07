"""Limpieza generativa de la foto de una prenda (OpenAI Images, endpoint /v1/images/edits)."""
from __future__ import annotations

import base64

import httpx

PROMPT = (
    "Product photo of ONLY the clothing item in this picture, isolated on a transparent background, "
    "as if laid flat or on an invisible mannequin, front view, centered, soft even lighting. "
    "Remove the person, hanger, furniture and any other objects. Keep the garment EXACTLY as it is: "
    "same colors, fabric, logos, prints, stitching and proportions. Do not add or invent anything."
)


class OpenAIImageCleaner:
    def __init__(self, api_key: str, model: str = "gpt-image-1", client: httpx.Client | None = None):
        self._model = model
        self._c = client or httpx.Client(
            base_url="https://api.openai.com/v1", headers={"Authorization": f"Bearer {api_key}"}, timeout=120
        )

    def __call__(self, jpg: bytes) -> bytes:
        r = self._c.post(
            "/images/edits",
            data={"model": self._model, "prompt": PROMPT, "background": "transparent",
                  "output_format": "png", "size": "1024x1024", "n": "1"},
            files={"image": ("item.jpg", jpg, "image/jpeg")},
        )
        r.raise_for_status()
        return base64.b64decode(r.json()["data"][0]["b64_json"])
