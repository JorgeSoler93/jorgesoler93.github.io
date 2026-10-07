"""Bot de Telegram. Solo traduce mensajes <-> service."""
from __future__ import annotations

import asyncio
import re

from .models import Item, Outfit, short
from .service import Closet, NotFound

HELP = """👔 *Armario*
📸 Manda una *foto* de una prenda (el pie de foto es tu comentario: «me queda grande», «para verano»…)
🔗 Manda un *enlace* de una prenda o de una foto
/armario [categoría] – lista (top, bottom, shoes, outerwear, dress, accessory)
/outfit [ocasión] [20°] [comentario] – te propongo conjuntos
/uso <id_conjunto> – me lo pongo hoy
/nota <id_conjunto> <1-5> – puntúa un conjunto
/sucia <id> · /limpia <id> – estado de lavado
/borrar <id> – elimina una prenda
/ver <id> – foto y ficha"""

URL_RE = re.compile(r"https?://\S+")
TEMP_RE = re.compile(r"(-?\d{1,2})\s*(?:°|º|grados|c\b)", re.I)


def fmt_item(i: Item) -> str:
    dirty = " 🧺" if i.status == "dirty" else ""
    return f"`{short(i.id)}` {i.name} · {', '.join(i.colors) or '?'} · {i.category}{dirty}"


def fmt_outfit(o: Outfit, items: list[Item]) -> str:
    lines = [f"*Conjunto* `{short(o.id)}`"] + [f"• {i.name} ({', '.join(i.colors)})" for i in items]
    return "\n".join(lines + [f"_{o.explanation}_"])


def parse_outfit_args(text: str) -> tuple[str, float | None, str]:
    """'trabajo 12° me han dicho que llueve' -> ('trabajo', 12.0, 'trabajo me han dicho...')"""
    m = TEMP_RE.search(text)
    temp = float(m.group(1)) if m else None
    rest = (text[: m.start()] + text[m.end() :]).strip() if m else text.strip()
    occasion = rest.split(" ")[0] if rest else ""
    return occasion, temp, rest


def run(closet: Closet, token: str, allowed: set[int]) -> None:  # pragma: no cover - requiere Telegram real
    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    ok = filters.User(user_id=list(allowed)) if allowed else filters.ALL

    async def reply(u: Update, text: str):
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    def safe(fn):
        async def wrapper(u: Update, c: ContextTypes.DEFAULT_TYPE):
            try:
                await fn(u, c)
            except NotFound as e:
                await u.message.reply_text(str(e))
            except Exception as e:
                await u.message.reply_text(f"⚠️ No pude: {e}")
        return wrapper

    async def start(u, c):
        await reply(u, HELP)

    async def photo(u, c):
        f = await u.message.photo[-1].get_file()
        data = bytes(await f.download_as_bytearray())
        await u.message.reply_text("Analizando la prenda… 🔍")
        item = await asyncio.to_thread(closet.add_from_photo, data, u.message.caption or "")
        await reply(u, "✅ Guardada:\n" + fmt_item(item))

    async def text(u, c):
        m = URL_RE.search(u.message.text)
        if not m:
            return await reply(u, HELP)
        await u.message.reply_text("Descargando y analizando… 🔍")
        item = await asyncio.to_thread(closet.add_from_url, m.group(0), URL_RE.sub("", u.message.text).strip())
        await reply(u, "✅ Guardada:\n" + fmt_item(item))

    async def armario(u, c):
        items = closet.list_items(c.args[0] if c.args else None)
        await reply(u, "\n".join(map(fmt_item, items[:40])) or "Aún no hay prendas. Mándame una foto 📸")

    async def outfit(u, c):
        occasion, temp, rest = parse_outfit_args(" ".join(c.args))
        outs = await asyncio.to_thread(closet.recommend, occasion, temp, rest)
        if not outs:
            return await reply(u, "No tengo prendas limpias suficientes (necesito parte de arriba y de abajo).")
        for o in outs:
            await reply(u, fmt_outfit(o, closet.outfit_items(o)))

    async def uso(u, c):
        o = closet.wear(c.args[0])
        await reply(u, f"👍 Anotado: `{short(o.id)}`")

    async def nota(u, c):
        o = closet.rate(c.args[0], int(c.args[1]))
        await reply(u, f"⭐ `{short(o.id)}` → {o.rating}/5")

    def status(value):
        async def h(u, c):
            await reply(u, fmt_item(closet.update_item(c.args[0], status=value)))
        return h

    async def borrar(u, c):
        await reply(u, f"🗑 Borrada: {closet.delete_item(c.args[0]).name}")

    async def ver(u, c):
        item = closet.get_item(c.args[0])
        with closet.image_path(item.id).open("rb") as fh:
            await u.message.reply_photo(fh, caption=fmt_item(item), parse_mode=ParseMode.MARKDOWN)

    app = Application.builder().token(token).build()
    for name, fn in [("start", start), ("ayuda", start), ("armario", armario), ("outfit", outfit), ("uso", uso),
                     ("nota", nota), ("sucia", status("dirty")), ("limpia", status("clean")), ("borrar", borrar), ("ver", ver)]:
        app.add_handler(CommandHandler(name, safe(fn), filters=ok))
    app.add_handler(MessageHandler(ok & filters.PHOTO, safe(photo)))
    app.add_handler(MessageHandler(ok & filters.TEXT & ~filters.COMMAND, safe(text)))
    app.run_polling()
