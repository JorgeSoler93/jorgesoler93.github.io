"""Descarga segura de una imagen a partir de un enlace (foto directa o página de producto)."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 3
UA = "Mozilla/5.0 (compatible; ArmarioBot/1.0)"
OG_IMAGE = re.compile(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']|'
                      r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:image["\']', re.I)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


class UnsafeURL(ValueError):
    pass


def check_url(url: str) -> None:
    """Evita SSRF: solo http(s) hacia IPs públicas."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UnsafeURL("Solo se admiten enlaces http(s)")
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror as e:
        raise UnsafeURL("No se pudo resolver el dominio") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UnsafeURL("Dirección no permitida")


def _get(client: httpx.Client, url: str) -> httpx.Response:
    for _ in range(MAX_REDIRECTS + 1):
        check_url(url)
        with client.stream("GET", url, headers={"User-Agent": UA}) as r:
            if r.is_redirect:
                url = urljoin(url, r.headers.get("location", ""))
                continue
            r.raise_for_status()
            body = b""
            for chunk in r.iter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    raise UnsafeURL("Archivo demasiado grande")
            return httpx.Response(r.status_code, headers=r.headers, content=body, request=r.request)
    raise UnsafeURL("Demasiadas redirecciones")


def fetch_image(url: str, client: httpx.Client | None = None) -> tuple[bytes, str]:
    """Devuelve (bytes_imagen, pista_de_texto). La pista es el título de la página si lo hay."""
    own = client is None
    client = client or httpx.Client(timeout=15, follow_redirects=False)
    try:
        r = _get(client, url)
        hint = ""
        if r.headers.get("content-type", "").startswith("text/html"):
            html = r.text
            m = OG_IMAGE.search(html)
            if not m:
                raise ValueError("No encontré imagen en esa página; mándame una foto o un enlace directo a la imagen")
            t = TITLE.search(html)
            hint = re.sub(r"\s+", " ", t.group(1)).strip() if t else ""
            r = _get(client, urljoin(url, m.group(1) or m.group(2)))
        if not r.headers.get("content-type", "").startswith("image/"):
            raise ValueError("El enlace no es una imagen")
        return r.content, hint
    finally:
        if own:
            client.close()
