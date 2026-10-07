# Cómo preparar las fotos con ChatGPT (mismo estilo para todo el armario)

1. Haz la foto de la prenda como puedas (cama, suelo, colgada). Da igual el fondo.
2. En ChatGPT, adjunta la foto y pega este prompt (si subes varias, repite el estilo en la misma conversación):

```
Convierte esta foto en una imagen de catálogo de ropa. Solo la prenda, sin persona, percha ni objetos.
Colócala frontal, centrada, planta o "maniquí invisible", sobre fondo BLANCO PURO liso (#FFFFFF), sin sombras
duras, iluminación suave y uniforme. Mantén exactamente los colores, estampados, logos, costuras y proporciones
de la prenda; no inventes nada. Formato cuadrado. Mismo estilo en todas las imágenes de esta conversación.
```

3. Descarga el resultado. **Fondo blanco puro es lo ideal**: la app lo recorta sola y deja la prenda transparente.
   Si ChatGPT te da PNG con transparencia, también vale y se respeta tal cual.
4. Mándalo a la app:
   - **Telegram:** como *archivo* (adjuntar → archivo), no como foto, para que no lo comprima. El pie = comentario.
   - **Carpeta (varias de golpe):** `top/camiseta-blanca.png`, `bottom/vaquero-azul.png`, `shoes/…` y
     `python -m closet import ./fotos`. La subcarpeta es la categoría y el nombre del archivo es el nombre.
   - **Web:** pestaña *Añadir*.
5. Si la app no tiene IA propia, el **agente** (tu ChatGPT en OpenClaw) mira la imagen y rellena los atributos
   (ver `HANDOFF.md`); si no, el color se detecta solo y el resto se corrige a mano.
