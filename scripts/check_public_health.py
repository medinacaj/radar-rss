#!/usr/bin/env python3
"""Check the public GitHub Pages publication without downloading RSS feeds."""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from site_config import DATA_URL

BASE = DATA_URL
STALE_HOURS = 18
MAX_ERRORS = 5

def read_json(name: str) -> dict:
    request = Request(BASE + name, headers={"User-Agent": "RadarRSS-HealthWatch/1.0", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=20) as response:
        payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError(f"Respuesta demasiado grande: {name}")
    doc = json.loads(payload)
    if not isinstance(doc, dict):
        raise ValueError(f"JSON inválido: {name}")
    return doc

def assess(meta: dict, status: dict, now: datetime, deploy_conclusion: str = "") -> list[str]:
    warnings = []
    if deploy_conclusion and deploy_conclusion not in ("success", "skipped", "cancelled", "neutral"):
        warnings.append(f"Última ejecución de publicación: {deploy_conclusion}")
    generated = meta.get("generated_at")
    checked = status.get("checked_at")
    try:
        created = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        measured = datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
        if created.tzinfo is None or measured.tzinfo is None:
            raise ValueError("Date without timezone")
    except (ValueError, TypeError):
        warnings.append("La fecha de actualización del sitio no es válida.")
        return warnings
    for key, dt in (("Noticias", created), ("Diagnóstico RSS", measured)):
        age = (now - dt).total_seconds() / 3600
        if age > STALE_HOURS:
            warnings.append(f"{key} sin actualizar hace {age:.1f} h (límite {STALE_HOURS} h)")
        elif age < -2:
            warnings.append(f"{key}: fecha futura incoherente ({age:.1f} h)")
    feeds = status.get("feeds")
    if not isinstance(feeds, list) or not feeds:
        warnings.append("Estado RSS sin listado de fuentes.")
    else:
        malformed = sum(not isinstance(feed, dict) or not isinstance(feed.get("state"), str) or not feed["state"].strip() for feed in feeds)
        if malformed:
            warnings.append(f"{malformed} entradas RSS sin estado válido.")
        errors = sum(isinstance(feed, dict) and feed.get("state") == "error" for feed in feeds)
        if errors >= MAX_ERRORS:
            warnings.append(f"{errors} fuentes RSS con errores (umbral {MAX_ERRORS})")
    if type(meta.get("total_articles")) is not int or meta["total_articles"] < 50:
        warnings.append("Historial público vacío o incompleto.")
    return warnings

def main() -> int:
    try:
        now = datetime.now(timezone.utc)
        meta, status = read_json("meta.json"), read_json("status.json")
        alerts = assess(meta, status, now, os.getenv("DEPLOY_CONCLUSION", ""))
    except Exception as exc:
        alerts = [f"No se pudo verificar el sitio público: {type(exc).__name__}: {exc}"]
    if alerts:
        print("ALERTA RADARRSS")
        for alert in alerts:
            print("- " + alert)
        return 1
    print("OK RADARRSS: noticia reciente, historial válido y menos de cinco RSS con error")
    return 0

if __name__ == "__main__":
    sys.exit(main())
