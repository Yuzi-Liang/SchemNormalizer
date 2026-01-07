from __future__ import annotations

from dataclasses import dataclass

from .model import Block
from .rules import RuleSet


@dataclass
class TransformStats:
    map_to_air: int = 0
    normalize_variants: int = 0
    strip_states: int = 0
    strip_nbt: int = 0


def map_to_air(block: Block, ruleset: RuleSet) -> tuple[Block, bool]:
    if block.id in ruleset.map_to_air_ids:
        return Block(id="minecraft:air", states={}, nbt=None), True
    return block, False


def normalize_variants(block: Block, ruleset: RuleSet) -> tuple[Block, bool]:
    rule = ruleset.normalize_map.get(block.id)
    if rule and rule.to_id != block.id:
        states = dict(block.states) if rule.preserve_states else {}
        nbt = block.nbt if rule.preserve_nbt else None
        return Block(id=rule.to_id, states=states, nbt=nbt), True
    return block, False


def strip_states(block: Block, ruleset: RuleSet) -> tuple[Block, bool]:
    # Clear states/NBT for specific ids after normalization.
    changed = False
    states = dict(block.states)
    nbt = block.nbt
    if block.id in ruleset.strip_states_ids and states:
        states = {}
        changed = True
    if block.id in ruleset.strip_nbt_ids and nbt is not None:
        nbt = None
        changed = True
    if changed:
        return Block(id=block.id, states=states, nbt=nbt), True
    return block, False
