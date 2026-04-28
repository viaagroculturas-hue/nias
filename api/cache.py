"""Cache JSON local para leituras externas do NIA$ v6.0."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CACHE_DIR = Path(
    os.environ.get(
        "NIAS_CACHE_DIR",
        Path(__file__).resolve().parents[1] / "data" / "cache",
    )
)


class CacheMiss(FileNotFoundError):
    """Indica que nao ha leitura valida em cache para a chave solicitada."""


class LocalJSONCache:
    """Persistencia simples em disco para a ultima leitura valida de cada API."""

    def __init__(self, base_dir: str | os.PathLike[str] | None = None) -> None:
        self.base_dir = Path(base_dir or DEFAULT_CACHE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
        safe_namespace = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in namespace)
        return self.base_dir / f"{safe_namespace}__{digest}.json"

    def save(
        self,
        namespace: str,
        key: str,
        payload: Any,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "namespace": namespace,
            "key": key,
            "source_url": source_url,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        path = self.path_for(namespace, key)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)
        return record

    def load(self, namespace: str, key: str) -> dict[str, Any]:
        path = self.path_for(namespace, key)
        if not path.exists():
            raise CacheMiss(f"Sem cache local para {namespace}:{key}")
        return json.loads(path.read_text(encoding="utf-8"))
