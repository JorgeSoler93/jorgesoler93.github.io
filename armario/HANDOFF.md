# Traspaso al mini PC

Copia el bloque de abajo y pégalo en tu agente del mini PC (el de OpenClaw). Está pensado para que **inspeccione tu montaje real antes de tocar nada**, porque desde aquí no puedo ver cómo está montado.

---

## Prompt para pegar

```
Quiero instalar en este mini PC una app nueva llamada "Armario" (recomendador de ropa).
Está desarrollada y testeada (22 tests) en el repo https://github.com/JorgeSoler93/jorgesoler93.github.io,
rama `claude/personal-ai-agent-app-18ukfc`, carpeta `armario/`. Lee `armario/README.md` primero.
NO es parte de Aura; es una app independiente.

PASO 0 — Inspecciona, no asumas. Antes de cambiar nada, dime:
 a) cómo están estructuradas mis otras apps/skills en este agente (lenguaje, carpeta, cómo se registran,
    cómo reciben mensajes de Telegram, cómo se sirven las web apps del hub);
 b) qué Supabase local uso (URL, puerto) y cómo guardan las otras apps sus credenciales;
 c) si ya hay un bot de Telegram en marcha: ¿conviene reutilizarlo (registrando los comandos de Armario
    en él) o usar el bot propio de `closet/telegram_bot.py` con otro token? Recomiéndame una y espera mi OK.

PASO 1 — Código: clona la rama y copia `armario/` a donde vayan mis apps. Crea un venv e instala `requirements.txt`.
Ejecuta `pytest` y confírmame que pasan los 22 tests.

PASO 2 — Base de datos: aplica `armario/supabase/migrations/001_armario.sql` en mi Supabase local
(tablas `armario_items` y `armario_outfits`, con prefijo para no chocar con las mías). Muéstrame el SQL
y pídeme confirmación antes de ejecutarlo. No toques ninguna tabla existente.

PASO 3 — Configuración: crea `.env` a partir de `.env.example` con SUPABASE_URL, SUPABASE_SERVICE_KEY,
ANTHROPIC_API_KEY (o dime qué proveedor de IA uso ya y adapta `closet/ai.py` implementando el protocolo `AI`
con `analyze_image` y `explain_outfits`), TELEGRAM_BOT_TOKEN y TELEGRAM_ALLOWED_IDS (solo mi user id).
Para la limpieza generativa de fotos, comprueba si ya tengo conectado OpenAI en este agente y con qué tipo de acceso
(clave de API o solo suscripción de ChatGPT): el endpoint de imágenes necesita clave de API con facturación. Si solo hay
suscripción, deja `OPENAI_API_KEY` vacío (usará el recorte clásico) y dímelo. Confirma el nombre vigente del modelo de
imagen y ajusta `ARMARIO_IMAGE_MODEL`.
Pídeme los secretos; no los inventes ni los subas a git.

PASO 4 — Integración:
 - Telegram: según lo decidido en 0c. Comandos: foto (pie = comentario), enlace, /armario, /outfit, /uso,
   /nota, /sucia, /limpia, /borrar, /ver.
 - Web/hub: monta `make_router(build())` de `closet/api.py` bajo `/armario` en mi hub (o ejecútalo con
   `python -m closet web 8085` detrás de Tailscale y enlázalo desde el hub). `index.html` usa rutas relativas.
 - Déjalo como servicio (systemd o como arranque mis otras apps) con reinicio automático.

PASO 5 — Prueba de humo real, una a una, contándome el resultado:
 1) mando por Telegram una foto de una camiseta con un comentario -> se guarda con atributos y recorte;
 2) mando un enlace de una prenda; 3) añado 3-4 prendas más; 4) /outfit trabajo 15°;
 5) abro la web desde el móvil por Tailscale y veo el armario.
Si algo falla, no lo maquilles: dime el error y propón arreglo.

Mejoras opcionales a proponerme al final (no las hagas sin preguntar): `rembg` para mejor recorte de fondo,
tiempo automático por geolocalización, y que Aura/otras apps puedan leer mi armario.
```

---

## Qué necesitas tener a mano
- Token del bot de Telegram (BotFather) y tu user id numérico.
- Clave de IA con visión (por defecto Anthropic).
- (Opcional) `OPENAI_API_KEY` de la API de OpenAI para la limpieza generativa de fotos.
- URL y service key de tu Supabase local.
