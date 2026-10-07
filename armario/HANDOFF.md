# Traspaso al mini PC

Copia el bloque de abajo y pégalo en tu agente del mini PC (el de OpenClaw). Está pensado para que **inspeccione tu montaje real antes de tocar nada**, porque desde aquí no puedo ver cómo está montado.

---

## Prompt para pegar

```
Quiero instalar en este mini PC una app nueva llamada "Armario" (recomendador de ropa).
Está desarrollada y testeada (27 tests) en el repo https://github.com/JorgeSoler93/jorgesoler93.github.io,
rama `claude/personal-ai-agent-app-18ukfc`, carpeta `armario/`. Lee `armario/README.md` y `armario/PROMPT_FOTOS.md` primero.
NO es parte de Aura; es una app independiente.

DISEÑO: la app NO tiene IA propia ni usa APIs de pago. Tú (el agente, con mi suscripción de ChatGPT) eres el cerebro:
 - La app guarda prendas, calcula conjuntos con reglas y sirve la web. `GET /api/schema` describe los atributos.
 - Cuando yo te mande una foto de una prenda (ya recortada por mí con ChatGPT), tú la miras, decides los atributos
   (name, category, subcategory, colors, pattern, material, formality 1-5, warmth 1-5, seasons, style_tags, notes) y llamas a
   `POST /api/items` (multipart: `photo`, `comment`, `attributes` = JSON). Si falta el color, la app lo calcula de los píxeles.
 - Cuando yo pida un conjunto, llamas a `POST /api/outfits/recommend {occasion, temp_c, comment}`, y redactas tú la respuesta
   con las prendas devueltas (la app ya trae una explicación breve por reglas). Para "me lo pongo": `POST /api/outfits/{id}/wear`.
 - Lo mismo para marcar sucia/limpia: `PATCH /api/items/{id} {"status":"dirty"}`.
 - Registra esto como una skill/herramienta de tu agente con el mismo formato que mis otras apps.

PASO 0 — Inspecciona, no asumas. Antes de cambiar nada, dime:
 a) cómo están estructuradas mis otras apps/skills (lenguaje, carpeta, cómo se registran, cómo reciben fotos y mensajes
    de Telegram, cómo se sirven las web apps del hub);
 b) qué Supabase local uso (URL, puerto) y cómo guardan las otras apps sus credenciales;
 c) si ya hay un bot de Telegram: ¿registramos Armario como skill del agente existente (recomendado, así no hay un segundo
    bot) o uso el bot propio de `closet/telegram_bot.py`? Recomiéndame una y espera mi OK.

PASO 1 — Copia `armario/` donde vayan mis apps, crea venv, `pip install -r requirements.txt` y ejecuta `pytest` (27 tests).

PASO 2 — Base de datos: muéstrame `armario/supabase/migrations/001_armario.sql` y, con mi OK, aplícalo en mi Supabase local
(tablas `armario_items` y `armario_outfits`). No toques tablas existentes.

PASO 3 — Configuración: `.env` desde `.env.example` con SUPABASE_URL y SUPABASE_SERVICE_KEY (pídemelas; no las inventes ni las
subas a git). Deja ANTHROPIC_API_KEY y OPENAI_API_KEY SIN definir. `rembg[cpu]` ya viene en requirements: úsalo para recortar
fondos y dime cuánto tarda con una foto de prueba.

PASO 4 — Integración: levanta la web (`python -m closet web 8085`, o montando `make_router(build())` en mi hub bajo
`/armario`) como servicio con reinicio automático, detrás de Tailscale. Crea la skill del agente que llame a la API como
se describe arriba. Para cargar muchas prendas de golpe: `python -m closet import ./carpeta` (subcarpetas top/bottom/shoes/...).

PASO 5 — Prueba de humo real, una a una, contándome el resultado:
 1) te mando por Telegram (como archivo) una camiseta recortada con un comentario -> la analizas y se guarda bien;
 2) añadimos 4-5 prendas más; 3) "qué me pongo para trabajar, hacen 12°" -> propuesta coherente;
 4) abro la web desde el móvil por Tailscale y veo el armario.
Si algo falla, no lo maquilles: dime el error y propón arreglo.
```

---

## Qué necesitas tener a mano
- URL y service key de tu Supabase local.
- Tus fotos recortadas con ChatGPT (ver `PROMPT_FOTOS.md`).
