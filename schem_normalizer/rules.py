from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ALLOWED_TRANSFORMS = {"map_to_air", "normalize_variants"}


@dataclass
class BlockMatch:
    ids: set[str]
    states: dict[str, str] | None = None


@dataclass
class NormalizeRule:
    match: BlockMatch
    to_id: str


@dataclass
class RuleSet:
    pipeline: list[str]
    map_to_air_ids: set[str]
    normalize_rules: list[NormalizeRule]
    normalize_map: dict[str, str]


class RuleError(ValueError):
    pass


def load_rules(path: Path) -> RuleSet:
    data = json.loads(path.read_text(encoding="utf-8"))
    return _parse_rules(data, path)


def _parse_rules(data: dict, source: Path) -> RuleSet:
    if not isinstance(data, dict):
        raise RuleError(f"Rules file must be a JSON object: {source}")

    version = data.get("version")
    if not isinstance(version, int):
        raise RuleError("Rules file must include integer 'version'.")

    pipeline = data.get("pipeline")
    if pipeline is None:
        pipeline = ["map_to_air", "normalize_variants"]
    if not isinstance(pipeline, list) or not all(isinstance(x, str) for x in pipeline):
        raise RuleError("'pipeline' must be a list of strings.")
    unknown = [name for name in pipeline if name not in ALLOWED_TRANSFORMS]
    if unknown:
        raise RuleError(f"Unknown pipeline transforms: {unknown}")

    map_to_air_ids = _parse_id_list(data.get("map_to_air", {}).get("ids", []), "map_to_air.ids")

    normalize_rules = _parse_normalize_rules(data.get("normalize_variants", []))
    normalize_map: dict[str, str] = {}
    for rule in normalize_rules:
        for block_id in rule.match.ids:
            if block_id in normalize_map and normalize_map[block_id] != rule.to_id:
                raise RuleError(f"Conflicting normalize rules for '{block_id}'.")
            normalize_map[block_id] = rule.to_id

    return RuleSet(
        pipeline=pipeline,
        map_to_air_ids=map_to_air_ids,
        normalize_rules=normalize_rules,
        normalize_map=normalize_map,
    )


def _parse_id_list(value: object, label: str) -> set[str]:
    if not isinstance(value, list):
        raise RuleError(f"'{label}' must be a list of strings.")
    ids: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise RuleError(f"'{label}' must contain non-empty strings.")
        ids.add(item)
    return ids


def _parse_normalize_rules(value: object) -> list[NormalizeRule]:
    if not isinstance(value, list):
        raise RuleError("'normalize_variants' must be a list.")

    rules: list[NormalizeRule] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise RuleError("Each normalize rule must be an object.")
        from_block = entry.get("from")
        to_block = entry.get("to")
        if not isinstance(from_block, dict) or not isinstance(to_block, dict):
            raise RuleError("Normalize rules must include 'from' and 'to' objects.")

        ids = _parse_id_list(from_block.get("ids", []), "normalize_variants.from.ids")
        if not ids:
            raise RuleError("normalize_variants.from.ids cannot be empty.")
        to_id = to_block.get("id")
        if not isinstance(to_id, str) or not to_id:
            raise RuleError("normalize_variants.to.id must be a non-empty string.")

        rules.append(NormalizeRule(match=BlockMatch(ids=ids), to_id=to_id))

    return rules
