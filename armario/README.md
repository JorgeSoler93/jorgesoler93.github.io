# Armario 👔

Catálogo de tu ropa + recomendador de conjuntos. Se usa por **Telegram** y como **web app** (para el hub).

```
foto / enlace / comentario ─► IA (visión) ─► atributos + recorte sin fondo ─► BD
                                                         │
 /outfit trabajo 12° ─► recomendador (reglas) ─► IA explica ─► conjuntos
```

## Piezas (`closet/`)
| Archivo | Qué hace |
|---|---|
| `models.py` | `Item`, `Outfit`, paleta de colores cerrada |
| `ai.py` | `ClaudeAI` (visión + explicaciones). `FakeAI` para tests. Proveedor intercambiable (`AI` protocol) |
| `imagegen.py` | limpieza **generativa** opcional de la foto (OpenAI Images) si hay `OPENAI_API_KEY` |
| `imaging.py` | normaliza foto y recorta el fondo (`rembg` si está, si no recorte por esquinas) |
| `urlfetch.py` | descarga imagen desde un enlace (foto directa u `og:image`), con protección SSRF |
| `recommender.py` | combina arriba+abajo+calzado(+abrigo) y puntúa: colores, formalidad, temperatura, ropa sucia, uso reciente |
| `repo.py` | `SQLiteRepo` (dev) y `SupabaseRepo` (PostgREST) con la misma interfaz |
| `service.py` | lógica de negocio; Telegram y web solo llaman aquí |
| `api.py` | `make_router(closet)` → se monta en tu hub; `create_app` la sirve sola |
| `telegram_bot.py` | comandos y handlers de foto/enlace |
| `web/index.html` | UI móvil (armario, añadir, conjuntos) |

## Sin IA propia (modo agente)
Si no hay `ANTHROPIC_API_KEY`, la app usa `HeuristicAI`: el color se calcula de los píxeles y el resto de atributos los pasa quien llama (`attributes` en `POST /api/items`, descritos en `GET /api/schema`) o una carpeta (`python -m closet import ./fotos`). Así el cerebro es tu agente. Cómo preparar las fotos: `PROMPT_FOTOS.md`.

## Arrancar
```bash
pip install -r requirements.txt
cp .env.example .env   # rellena claves
export $(grep -v '^#' .env | xargs)
python -m closet web 8085   # web + API
python -m closet bot        # Telegram
pytest                      # 27 tests, sin red ni claves
```
Sin `SUPABASE_URL` usa SQLite en `./data`. Para Supabase: ejecuta `supabase/migrations/001_armario.sql`.

## Comandos de Telegram
Foto (pie de foto = comentario) · enlace · `/armario [cat]` · `/outfit [ocasión] [20°] [comentario]` · `/uso id` · `/nota id 1-5` · `/sucia id` · `/limpia id` · `/borrar id` · `/ver id`

## Meterlo en el hub (FastAPI)
```python
from closet.service import build
from closet.api import make_router
hub.include_router(make_router(build()), prefix="/armario")
```
(`index.html` usa rutas relativas, así que funciona bajo cualquier prefijo.)

## Límites conocidos
- Por defecto no sale ninguna foto del equipo: recorte local (`rembg` si lo instalas, gratis; si no, recorte simple). Opcional y de pago: con `OPENAI_API_KEY` la foto se rehace con un modelo generativo (solo la prenda, fondo transparente). Si falla o no hay clave, cae al recorte clásico (rembg / flood-fill). Un modelo generativo puede alterar detalles (logos, estampados): el original se conserva siempre (`image_file`) y la ficha se extrae del original, no de la versión generada.
- Enlaces de tiendas que bloquean bots o cargan la foto con JavaScript no funcionan: en ese caso, pasa la foto.
- `SupabaseRepo` está probado con un servidor simulado, no contra tu Supabase real.
- El tiempo se pasa a mano (`/outfit 12°`); conectar un servicio meteorológico es una ampliación sencilla.
