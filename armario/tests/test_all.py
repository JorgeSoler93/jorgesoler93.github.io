import io
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from closet import imaging, recommender, urlfetch
from closet.ai import FakeAI, extract_json
from closet.api import make_router
from closet.models import Item, ItemAttributes
from closet.repo import SQLiteRepo, SupabaseRepo
from closet.service import Closet, NotFound
from closet.telegram_bot import parse_outfit_args


def photo(color=(200, 30, 30), bg=(240, 240, 240)) -> bytes:
    img = Image.new("RGB", (120, 120), bg)
    img.paste(Image.new("RGB", (60, 60), color), (30, 30))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def closet(tmp_path):
    return Closet(SQLiteRepo(str(tmp_path / "t.db")), FakeAI(), tmp_path)


def mk(closet, **kw):
    attrs = {"name": "x", "category": "top", "colors": ["blanco"], **kw}
    closet.ai.attrs = ItemAttributes(**attrs)
    return closet.add_from_photo(photo(), "comentario")


# ---------- imaging ----------
def test_cutout_makes_background_transparent():
    png = Image.open(io.BytesIO(imaging.remove_background(photo())))
    assert png.mode == "RGBA" and max(png.size) < 80  # recortado al objeto (original 120)
    assert png.getpixel((30, 30))[3] == 255


def test_bad_image():
    with pytest.raises(imaging.BadImage):
        imaging.normalize(b"no soy una imagen")


# ---------- repo + service ----------
def test_add_item_roundtrip_and_comment(closet):
    it = mk(closet, name="Camiseta", colors=["blanco", "azul"])
    got = closet.get_item(it.id[:6])
    assert got.colors == ["blanco", "azul"] and got.notes == "comentario"
    assert closet.image_path(it.id).suffix == ".png" and closet.image_path(it.id).exists()


def test_update_validates_and_delete_removes_files(closet):
    it = mk(closet)
    assert closet.update_item(it.id, status="dirty").status == "dirty"
    with pytest.raises(Exception):
        closet.update_item(it.id, formality=9)
    closet.delete_item(it.id)
    assert closet.list_items() == []
    with pytest.raises(NotFound):
        closet.get_item(it.id)


# ---------- recommender ----------
def wardrobe(closet):
    mk(closet, name="Camiseta blanca", category="top", colors=["blanco"], formality=2, warmth=1)
    mk(closet, name="Jersey gris", category="top", colors=["gris"], formality=2, warmth=4)
    mk(closet, name="Vaquero", category="bottom", colors=["azul marino"], formality=2, warmth=3)
    mk(closet, name="Zapatillas", category="shoes", colors=["blanco"], formality=2, warmth=2)
    mk(closet, name="Abrigo", category="outerwear", colors=["negro"], formality=3, warmth=5)


def test_recommend_respects_temperature(closet):
    wardrobe(closet)
    hot = closet.recommend("casual", 30)[0]
    cold = closet.recommend("casual", 3)[0]
    assert "Camiseta blanca" in [i.name for i in closet.outfit_items(hot)]
    assert "Abrigo" not in [i.name for i in closet.outfit_items(hot)]
    names = [i.name for i in closet.outfit_items(cold)]
    assert "Jersey gris" in names and "Abrigo" in names


def test_dirty_items_are_excluded_and_empty_closet(closet):
    assert closet.recommend("casual") == []
    wardrobe(closet)
    for i in closet.list_items("bottom"):
        closet.update_item(i.id, status="dirty")
    assert closet.recommend("casual") == []


def test_wear_updates_counters_and_penalizes_recent(closet):
    wardrobe(closet)
    mk(closet, name="Polo", category="top", colors=["beige"], formality=2, warmth=1)
    first = closet.recommend("casual", 22)[0]
    closet.wear(first.id[:6])
    assert all(i.wear_count == 1 and i.last_worn for i in closet.outfit_items(first))
    second = closet.recommend("casual", 22)[0]
    assert set(second.item_ids) != set(first.item_ids)


def test_color_clash_scores_lower():
    a = Item(name="a", colors=["rojo"]); b = Item(name="b", category="bottom", colors=["verde"])
    c = Item(name="c", category="bottom", colors=["azul marino"])
    now = datetime.now(timezone.utc)
    clash = recommender.score_outfit([a, b], formality=None, temp_c=None, now=now)
    fine = recommender.score_outfit([a, c], formality=None, temp_c=None, now=now)
    assert fine.score > clash.score


def test_rate_validation(closet):
    wardrobe(closet)
    o = closet.recommend("casual")[0]
    assert closet.rate(o.id, 5).rating == 5
    with pytest.raises(ValueError):
        closet.rate(o.id, 9)


# ---------- api ----------
def client(closet, token=""):
    app = FastAPI(); app.include_router(make_router(closet, token))
    return TestClient(app)


def test_api_flow(closet):
    c = client(closet)
    r = c.post("/api/items", files={"photo": ("a.jpg", photo(), "image/jpeg")}, data={"comment": "hola"})
    assert r.status_code == 200
    iid = r.json()["id"]
    assert c.get(f"/api/items/{iid}/image").headers["content-type"] == "image/png"
    assert c.patch(f"/api/items/{iid}", json={"name": "Nueva"}).json()["name"] == "Nueva"
    assert c.get("/api/items?category=top").json()[0]["name"] == "Nueva"
    assert c.post("/api/items", files={"photo": ("a.jpg", b"basura", "image/jpeg")}).status_code == 400
    assert c.get("/api/items/zzz/image").status_code == 404
    assert c.delete(f"/api/items/{iid}").json() == {"deleted": iid}


def test_api_recommend_and_wear(closet):
    wardrobe(closet)
    c = client(closet)
    outs = c.post("/api/outfits/recommend", json={"occasion": "casual", "temp_c": 20}).json()
    assert outs and outs[0]["items"]
    assert c.post(f"/api/outfits/{outs[0]['id']}/wear").json()["worn_on"]


def test_api_token(closet):
    c = client(closet, "secreto")
    assert c.get("/api/items").status_code == 401
    assert c.get("/api/items", headers={"Authorization": "Bearer secreto"}).status_code == 200
    assert c.get("/api/items?token=secreto").status_code == 200


# ---------- urlfetch ----------
@pytest.mark.parametrize("u", ["file:///etc/passwd", "http://127.0.0.1/x", "http://localhost/x", "http://192.168.1.5/x", "ftp://a.com/x"])
def test_ssrf_blocked(u):
    with pytest.raises(urlfetch.UnsafeURL):
        urlfetch.check_url(u)


def test_add_from_url_via_og_image(closet, monkeypatch):
    monkeypatch.setattr(urlfetch, "check_url", lambda u: None)
    jpg = photo()

    def handler(req):
        import httpx
        if req.url.path == "/p":
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  text='<title>Polo azul</title><meta property="og:image" content="/img.jpg">')
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=jpg)

    import httpx
    client_ = httpx.Client(transport=httpx.MockTransport(handler))
    data, hint = urlfetch.fetch_image("https://tienda.test/p", client_)
    assert data == jpg and hint == "Polo azul"


# ---------- misc ----------
def test_supabase_repo_speaks_postgrest():
    import httpx
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path, dict(req.url.params)))
        return httpx.Response(200, json=[Item(name="n").model_dump()])

    repo = SupabaseRepo("http://x", "k", httpx.Client(base_url="http://x/rest/v1", transport=httpx.MockTransport(handler)))
    it = repo.list_items("top")[0]
    repo.update_item(it.id, status="dirty")
    assert seen[0] == ("GET", "/rest/v1/armario_items", {"order": "created_at.desc", "category": "eq.top"})
    assert seen[1][0] == "PATCH"


def test_extract_json_tolerates_prose():
    assert extract_json('Claro:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_outfit_args():
    assert parse_outfit_args("trabajo 12° lluvia") == ("trabajo", 12.0, "trabajo  lluvia")
    assert parse_outfit_args("") == ("", None, "")


def test_claude_ai_parses_response_with_stub_client():
    from types import SimpleNamespace as NS

    from closet.ai import ClaudeAI

    sent = {}

    class Stub:
        class messages:  # noqa: N801
            @staticmethod
            def create(**kw):
                sent.update(kw)
                txt = '```json\n{"name":"Polo","category":"top","colors":["Azul Marino "," azul marino"],"formality":3}\n```'
                return NS(content=[NS(type="text", text=txt)])

    ai = ClaudeAI("k", "m", client=Stub())
    attrs = ai.analyze_image(b"x", "image/jpeg", "me queda grande")
    assert attrs.colors == ["azul marino"] and attrs.formality == 3
    assert "me queda grande" in sent["messages"][0]["content"][1]["text"]
