from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


def _extract_quoted(line: str) -> str:
    m = re.search(r'"([^"]+)"', line)
    return m.group(1) if m else ""


def load_metric_catalog(metrics_path: str = "semantic/metrics.yaml") -> List[Dict[str, object]]:
    """
    Lightweight parser for current metrics.yaml structure without external deps.
    Extracts metric key, concept_id, names, aliases, definition.
    """
    path = Path(metrics_path)
    lines = path.read_text(encoding="utf-8").splitlines()

    catalog: List[Dict[str, object]] = []
    current: Dict[str, object] | None = None
    in_aliases = False

    for raw in lines:
        line = raw.rstrip("\n")

        metric_start = re.match(r"^\s{2}([a-zA-Z0-9_]+):\s*$", line)
        if metric_start:
            if current:
                catalog.append(current)
            current = {
                "metric_key": metric_start.group(1),
                "metric_id": metric_start.group(1),
                "concept_id": metric_start.group(1),
                "aliases": [],
                "name_zh": "",
                "name_en": "",
                "definition_zh": "",
            }
            in_aliases = False
            continue

        if current is None:
            continue

        stripped = line.strip()
        if stripped.startswith("concept_id:"):
            value = _extract_quoted(stripped)
            if value:
                current["concept_id"] = value
                current["metric_id"] = value
            in_aliases = False
        elif stripped.startswith("name_zh:"):
            current["name_zh"] = _extract_quoted(stripped)
            in_aliases = False
        elif stripped.startswith("name_en:"):
            current["name_en"] = _extract_quoted(stripped)
            in_aliases = False
        elif stripped.startswith("definition_zh:"):
            current["definition_zh"] = _extract_quoted(stripped)
            in_aliases = False
        elif stripped.startswith("aliases:"):
            in_aliases = True
        elif in_aliases and stripped.startswith("-"):
            current["aliases"].append(_extract_quoted(stripped))
        elif stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            if re.match(r"^[a-zA-Z_]+:", stripped):
                in_aliases = False

    if current:
        catalog.append(current)

    return catalog


def retrieve_metric_hints(normalized_text: str, catalog: List[Dict[str, object]], top_k: int = 3) -> List[str]:
    tokens = [t for t in re.split(r"\s+", normalized_text.lower()) if t]
    scored: List[Tuple[str, int]] = []

    for metric in catalog:
        score = 0
        fields = [
            str(metric.get("name_zh", "")).lower(),
            str(metric.get("name_en", "")).lower(),
            str(metric.get("definition_zh", "")).lower(),
        ] + [str(a).lower() for a in metric.get("aliases", [])]

        for token in tokens:
            if any(token in field for field in fields if field):
                score += 1

        # useful for Chinese queries with no explicit spaces
        for alias in metric.get("aliases", []):
            alias_l = str(alias).lower()
            if alias_l and alias_l in normalized_text.lower():
                score += 2

        if score > 0:
            scored.append((str(metric.get("metric_id")), score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [metric_id for metric_id, _ in scored[:top_k]]
