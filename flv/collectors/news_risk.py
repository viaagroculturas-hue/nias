"""
NLP leve para notícias agrícolas — índice de risco.

Implementação inicial: RSS + regras/keywords com pesos.
Depois pode evoluir para embeddings + classificador.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape


KEYWORDS = [
    # Gatilhos solicitados: pesos altos porque representam choques sistêmicos.
    (r"\bgreve\s+de\s+caminhoneir\w*", 1.00, "GREVE_CAMINHONEIROS"),
    (r"\bguerra\s+na\s+ucr[aâ]nia\b", 0.90, "GUERRA_UCRANIA"),
    (r"\bseca\s+no\s+canal\s+do\s+panam[aá]\b", 0.90, "SECA_CANAL_PANAMA"),
    # logística/energia
    (r"\bparalisa\w*", 0.55, "PARALISACAO"),
    (r"\bbloqueio\b|\binterdi\w*", 0.45, "BLOQUEIO"),
    (r"\bdiesel\b|\bfrete\b|\btransporte\b", 0.30, "LOGISTICA_CUSTO"),
    # geopolítica
    (r"\bucr[aâ]nia\b|\brussia\b|\br[úu]ssia\b", 0.55, "UCRANIA"),
    (r"\bsan[cç][aã]o\w*|\bembargo\b", 0.55, "SANCOES"),
    # clima global/logística marítima
    (r"\bcanal\s+do\s+panam[aá]\b|\bpanama canal\b", 0.65, "PANAMA"),
    (r"\bel\s*ni[nñ]o\b|\boni\b", 0.40, "EL_NINO"),
    (r"\bla\s*ni[nñ]a\b", 0.35, "LA_NINA"),
    (r"\bquebra\s+de\s+safra\b|\bcrop failure\b", 0.50, "QUEBRA_SAFRA"),
]


DEFAULT_FEEDS = [
    # Reuters/Bloomberg são normalmente pagos; aqui fica o “gancho” para URLs RSS se você tiver.
    # Você pode trocar/adiantar os endpoints depois.
    ("NoticiasAgricolas", "https://www.noticiasagricolas.com.br/rss/noticias.rss"),
]


def _feeds_from_env() -> list[tuple[str, str]]:
    """
    Lê feeds adicionais de FLV_NEWS_RSS_FEEDS.

    Formatos aceitos:
    - JSON: [{"source":"Reuters","url":"https://..."}, ...]
    - Texto: "Reuters|https://...;Bloomberg|https://..."
    """
    raw = os.environ.get("FLV_NEWS_RSS_FEEDS", "").strip()
    if not raw:
        return []
    feeds: list[tuple[str, str]] = []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("source") and item.get("url"):
                    feeds.append((str(item["source"]), str(item["url"])))
        if feeds:
            return feeds
    except Exception:
        pass
    for part in raw.split(";"):
        if "|" not in part:
            continue
        source, url = [p.strip() for p in part.split("|", 1)]
        if source and url:
            feeds.append((source, url))
    return feeds


def _fetch(url: str, timeout=20) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_rss(xml_text: str) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or item.findtext("summary") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        items.append({
            "title": unescape(re.sub(r"<[^>]+>", " ", title)).strip(),
            "description": unescape(re.sub(r"<[^>]+>", " ", description)).strip(),
            "url": link,
            "pubDate": pub,
        })
    return items


def _score_text(text: str) -> tuple[float, list[str]]:
    t = (text or "").lower()
    score = 0.0
    tags = []
    for pat, w, tag in KEYWORDS:
        if re.search(pat, t, flags=re.IGNORECASE):
            score += w
            tags.append(tag)
    score = min(1.0, score)
    return score, tags


def coletar_indice_risco_noticias(feeds=None, max_items_per_feed=25):
    """
    Lê RSS feeds, detecta eventos e grava:
    - `flv_news_events` (eventos individuais)
    - `flv_news_risk_daily` (índice agregado por dia)
    """
    from flv.db import init_db, insert_news_event, upsert_news_risk_daily

    try:
        init_db()
    except Exception:
        pass

    feeds = feeds or (_feeds_from_env() + DEFAULT_FEEDS)
    now = datetime.now(timezone.utc)
    obs_ts = now.isoformat()
    obs_date = now.strftime("%Y-%m-%d")

    all_scores = []
    tag_counts = {}
    sources = set()
    seen = set()

    for source, url in feeds:
        try:
            xml_text = _fetch(url, timeout=20)
            if not xml_text:
                continue
            sources.add(source)
            items = _parse_rss(xml_text)[:max_items_per_feed]
            for it in items:
                title = it.get("title") or ""
                body = f"{title} {it.get('description') or ''}"
                dedupe_key = (it.get("url") or title).strip().lower()
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                s, tags = _score_text(body)
                if s <= 0:
                    continue
                all_scores.append(s)
                for tg in tags:
                    tag_counts[tg] = tag_counts.get(tg, 0) + 1
                insert_news_event(
                    obs_ts=obs_ts,
                    source=source,
                    title=title[:500],
                    url=(it.get("url") or "")[:1000],
                    risk_score=s,
                    tags_json=json.dumps(tags, ensure_ascii=False),
                )
        except Exception:
            continue

    # Agregação simples: média truncada + boost por frequência
    if all_scores:
        base = sum(all_scores) / len(all_scores)
        freq_boost = min(0.35, 0.05 * sum(1 for _ in all_scores))
        risk_index = float(min(1.0, base + freq_boost))
    else:
        risk_index = 0.0

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    upsert_news_risk_daily(
        obs_date=obs_date,
        risk_index=risk_index,
        top_tags_json=json.dumps(top_tags, ensure_ascii=False),
        sources_json=json.dumps(sorted(list(sources)), ensure_ascii=False),
    )

    print(f"[FLV-NewsRisk] {obs_date} risk_index={risk_index:.2f} tags={top_tags[:3]}")
    return {"obs_date": obs_date, "risk_index": risk_index, "top_tags": top_tags, "sources": sorted(list(sources))}

