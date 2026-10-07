"""Persistencia. Misma interfaz para SQLite (desarrollo) y Supabase/PostgREST (mini PC)."""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Protocol

import httpx

from .models import Item, Outfit, now_iso

ITEM_LISTS = ("colors", "seasons", "style_tags")
ITEM_COLS = list(Item.model_fields)
OUTFIT_COLS = list(Outfit.model_fields)


class Repo(Protocol):
    def add_item(self, item: Item) -> Item: ...
    def get_item(self, id_: str) -> Item | None: ...
    def list_items(self, category: str | None = None) -> list[Item]: ...
    def update_item(self, id_: str, **fields: Any) -> Item | None: ...
    def delete_item(self, id_: str) -> bool: ...
    def add_outfit(self, outfit: Outfit) -> Outfit: ...
    def get_outfit(self, id_: str) -> Outfit | None: ...
    def list_outfits(self, limit: int = 20) -> list[Outfit]: ...
    def update_outfit(self, id_: str, **fields: Any) -> Outfit | None: ...


class SQLiteRepo:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        item_cols = ", ".join(f"{c} TEXT" if c not in ("formality", "warmth", "wear_count") else f"{c} INTEGER" for c in ITEM_COLS if c != "id")
        out_cols = ", ".join(c + (" REAL" if c == "score" else " INTEGER" if c == "rating" else " TEXT") for c in OUTFIT_COLS if c != "id")
        with self._lock:
            self._db.execute(f"CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, {item_cols})")
            self._db.execute(f"CREATE TABLE IF NOT EXISTS outfits (id TEXT PRIMARY KEY, {out_cols})")
            self._db.commit()

    # -- helpers --
    @staticmethod
    def _enc(table: str, d: dict) -> dict:
        d = dict(d)
        for k, v in d.items():
            if isinstance(v, list):
                d[k] = json.dumps(v, ensure_ascii=False)
        return d

    @staticmethod
    def _dec(row: sqlite3.Row) -> dict:
        d = dict(row)
        for k, v in d.items():
            if k in ITEM_LISTS or k == "item_ids":
                d[k] = json.loads(v) if v else []
        return d

    def _insert(self, table: str, data: dict) -> None:
        data = self._enc(table, data)
        cols = ", ".join(data)
        marks = ", ".join("?" for _ in data)
        with self._lock:
            self._db.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(data.values()))
            self._db.commit()

    def _get(self, table: str, id_: str) -> dict | None:
        with self._lock:
            row = self._db.execute(f"SELECT * FROM {table} WHERE id = ?", (id_,)).fetchone()
        return self._dec(row) if row else None

    def _update(self, table: str, id_: str, fields: dict) -> None:
        if not fields:
            return
        fields = self._enc(table, fields)
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self._db.execute(f"UPDATE {table} SET {sets} WHERE id = ?", [*fields.values(), id_])
            self._db.commit()

    # -- items --
    def add_item(self, item: Item) -> Item:
        self._insert("items", item.model_dump())
        return item

    def get_item(self, id_: str) -> Item | None:
        d = self._get("items", id_)
        return Item(**d) if d else None

    def list_items(self, category: str | None = None) -> list[Item]:
        q, args = "SELECT * FROM items", []
        if category:
            q += " WHERE category = ?"
            args.append(category)
        with self._lock:
            rows = self._db.execute(q + " ORDER BY created_at DESC", args).fetchall()
        return [Item(**self._dec(r)) for r in rows]

    def update_item(self, id_: str, **fields: Any) -> Item | None:
        self._update("items", id_, fields)
        return self.get_item(id_)

    def delete_item(self, id_: str) -> bool:
        with self._lock:
            cur = self._db.execute("DELETE FROM items WHERE id = ?", (id_,))
            self._db.commit()
        return cur.rowcount > 0

    # -- outfits --
    def add_outfit(self, outfit: Outfit) -> Outfit:
        self._insert("outfits", outfit.model_dump())
        return outfit

    def get_outfit(self, id_: str) -> Outfit | None:
        d = self._get("outfits", id_)
        return Outfit(**d) if d else None

    def list_outfits(self, limit: int = 20) -> list[Outfit]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM outfits ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Outfit(**self._dec(r)) for r in rows]

    def update_outfit(self, id_: str, **fields: Any) -> Outfit | None:
        self._update("outfits", id_, fields)
        return self.get_outfit(id_)


class SupabaseRepo:
    """PostgREST (lo que expone Supabase). Tablas: armario_items / armario_outfits."""

    def __init__(self, url: str, key: str, client: httpx.Client | None = None):
        self._c = client or httpx.Client(
            base_url=f"{url}/rest/v1",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "return=representation"},
            timeout=15,
        )

    def _req(self, method: str, table: str, **kw) -> list[dict]:
        r = self._c.request(method, f"/armario_{table}", **kw)
        r.raise_for_status()
        return r.json() if r.content else []

    def _one(self, table: str, id_: str) -> dict | None:
        rows = self._req("GET", table, params={"id": f"eq.{id_}"})
        return rows[0] if rows else None

    def add_item(self, item: Item) -> Item:
        self._req("POST", "items", json=item.model_dump())
        return item

    def get_item(self, id_: str) -> Item | None:
        d = self._one("items", id_)
        return Item(**d) if d else None

    def list_items(self, category: str | None = None) -> list[Item]:
        params = {"order": "created_at.desc"}
        if category:
            params["category"] = f"eq.{category}"
        return [Item(**d) for d in self._req("GET", "items", params=params)]

    def update_item(self, id_: str, **fields: Any) -> Item | None:
        rows = self._req("PATCH", "items", params={"id": f"eq.{id_}"}, json=fields) if fields else [self._one("items", id_)]
        return Item(**rows[0]) if rows and rows[0] else None

    def delete_item(self, id_: str) -> bool:
        return bool(self._req("DELETE", "items", params={"id": f"eq.{id_}"}))

    def add_outfit(self, outfit: Outfit) -> Outfit:
        self._req("POST", "outfits", json=outfit.model_dump())
        return outfit

    def get_outfit(self, id_: str) -> Outfit | None:
        d = self._one("outfits", id_)
        return Outfit(**d) if d else None

    def list_outfits(self, limit: int = 20) -> list[Outfit]:
        return [Outfit(**d) for d in self._req("GET", "outfits", params={"order": "created_at.desc", "limit": limit})]

    def update_outfit(self, id_: str, **fields: Any) -> Outfit | None:
        rows = self._req("PATCH", "outfits", params={"id": f"eq.{id_}"}, json=fields) if fields else [self._one("outfits", id_)]
        return Outfit(**rows[0]) if rows and rows[0] else None
