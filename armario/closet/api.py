"""API REST + web app. `router` se puede incluir en tu hub; `create_app` la sirve sola."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import imaging, urlfetch
from .models import Item, Outfit
from .service import Closet, NotFound, build

WEB = Path(__file__).parent / "web"


class FromUrl(BaseModel):
    url: str
    comment: str = ""


class RecommendReq(BaseModel):
    occasion: str = ""
    temp_c: float | None = None
    comment: str = ""
    limit: int = 3


class ItemPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    subcategory: str | None = None
    colors: list[str] | None = None
    formality: int | None = None
    warmth: int | None = None
    seasons: list[str] | None = None
    notes: str | None = None
    status: str | None = None


def make_router(closet: Closet, api_token: str = "") -> APIRouter:
    def auth(request: Request):
        if api_token and (request.headers.get("authorization") != f"Bearer {api_token}" and request.query_params.get("token") != api_token):
            raise HTTPException(401, "Token incorrecto")

    r = APIRouter(dependencies=[Depends(auth)])

    def guard(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except NotFound as e:
            raise HTTPException(404, str(e))
        except (imaging.BadImage, urlfetch.UnsafeURL, ValueError) as e:
            raise HTTPException(400, str(e))
        except Exception as e:  # fallo de IA / red / validación
            raise HTTPException(502, f"Error procesando la petición: {e}")

    def view_outfit(o: Outfit) -> dict:
        return {**o.model_dump(), "items": [i.model_dump() for i in closet.outfit_items(o)]}

    @r.get("/api/items")
    def list_items(category: str | None = None) -> list[Item]:
        return closet.list_items(category)

    @r.post("/api/items")
    def add_item(photo: UploadFile = File(...), comment: str = Form("")) -> Item:
        return guard(closet.add_from_photo, photo.file.read(), comment)

    @r.post("/api/items/from-url")
    def add_from_url(body: FromUrl) -> Item:
        return guard(closet.add_from_url, body.url, body.comment)

    @r.patch("/api/items/{ref}")
    def patch_item(ref: str, body: ItemPatch) -> Item:
        return guard(closet.update_item, ref, **body.model_dump(exclude_none=True))

    @r.delete("/api/items/{ref}")
    def delete_item(ref: str) -> dict:
        return {"deleted": guard(closet.delete_item, ref).id}

    @r.get("/api/items/{ref}/image")
    def image(ref: str, clean: bool = True):
        path = guard(closet.image_path, ref, clean)
        if not path.is_file():
            raise HTTPException(404, "Sin imagen")
        return FileResponse(path)

    @r.post("/api/outfits/recommend")
    def recommend(body: RecommendReq) -> list[dict]:
        return [view_outfit(o) for o in guard(closet.recommend, body.occasion, body.temp_c, body.comment, body.limit)]

    @r.post("/api/outfits/{ref}/wear")
    def wear(ref: str) -> dict:
        return view_outfit(guard(closet.wear, ref))

    @r.post("/api/outfits/{ref}/rate")
    def rate(ref: str, rating: int) -> dict:
        return view_outfit(guard(closet.rate, ref, rating))

    @r.get("/", include_in_schema=False)
    def index():
        return FileResponse(WEB / "index.html")

    return r


def create_app(closet: Closet | None = None, api_token: str | None = None) -> FastAPI:
    from .config import Settings

    s = Settings.from_env()
    app = FastAPI(title="Armario")
    app.include_router(make_router(closet or build(s), s.api_token if api_token is None else api_token))
    return app
