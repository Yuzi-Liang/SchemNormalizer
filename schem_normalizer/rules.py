from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ALLOWED_TRANSFORMS = {"map_to_air", "normalize_variants", "strip_states"}


@dataclass
class BlockMatch:
    ids: set[str]
    states: dict[str, str] | None = None


@dataclass
class NormalizeRule:
    match: BlockMatch
    to_id: str
    preserve_states: bool = True
    preserve_nbt: bool = True


@dataclass
class RuleSet:
    pipeline: list[str]
    map_to_air_ids: set[str]
    normalize_rules: list[NormalizeRule]
    normalize_map: dict[str, NormalizeRule]
    default_preserve_states: bool = True
    default_preserve_nbt: bool = True
    strip_states_ids: set[str] = field(default_factory=set)
    strip_nbt_ids: set[str] = field(default_factory=set)


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

    defaults = data.get("normalize_defaults", {})
    if defaults is None:
        defaults = {}
    if not isinstance(defaults, dict):
        raise RuleError("'normalize_defaults' must be an object.")
    default_preserve_states = defaults.get("preserve_states", True)
    default_preserve_nbt = defaults.get("preserve_nbt", True)
    if not isinstance(default_preserve_states, bool):
        raise RuleError("normalize_defaults.preserve_states must be a boolean.")
    if not isinstance(default_preserve_nbt, bool):
        raise RuleError("normalize_defaults.preserve_nbt must be a boolean.")

    normalize_rules = _parse_normalize_rules(
        data.get("normalize_variants", []),
        default_preserve_states,
        default_preserve_nbt,
    )
    normalize_map: dict[str, NormalizeRule] = {}
    for rule in normalize_rules:
        for block_id in rule.match.ids:
            if block_id in normalize_map:
                existing = normalize_map[block_id]
                if (
                    existing.to_id != rule.to_id
                    or existing.preserve_states != rule.preserve_states
                    or existing.preserve_nbt != rule.preserve_nbt
                ):
                    raise RuleError(f"Conflicting normalize rules for '{block_id}'.")
            normalize_map[block_id] = rule

    strip_states_ids = _parse_id_list(data.get("strip_states", {}).get("ids", []), "strip_states.ids")
    strip_nbt_ids = _parse_id_list(data.get("strip_nbt", {}).get("ids", []), "strip_nbt.ids")

    return RuleSet(
        pipeline=pipeline,
        map_to_air_ids=map_to_air_ids,
        normalize_rules=normalize_rules,
        normalize_map=normalize_map,
        default_preserve_states=default_preserve_states,
        default_preserve_nbt=default_preserve_nbt,
        strip_states_ids=strip_states_ids,
        strip_nbt_ids=strip_nbt_ids,
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


def _parse_normalize_rules(
    value: object,
    default_preserve_states: bool,
    default_preserve_nbt: bool,
) -> list[NormalizeRule]:
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

        preserve_states = entry.get("preserve_states", default_preserve_states)
        preserve_nbt = entry.get("preserve_nbt", default_preserve_nbt)
        if not isinstance(preserve_states, bool):
            raise RuleError("normalize_variants.preserve_states must be a boolean.")
        if not isinstance(preserve_nbt, bool):
            raise RuleError("normalize_variants.preserve_nbt must be a boolean.")

        rules.append(
            NormalizeRule(
                match=BlockMatch(ids=ids),
                to_id=to_id,
                preserve_states=preserve_states,
                preserve_nbt=preserve_nbt,
            )
        )

    return rules
