from __future__ import annotations

from dataclasses import dataclass

from .model import Block
from .rules import RuleSet


@dataclass
class TransformStats:
    map_to_air: int = 0
    normalize_variants: int = 0


def map_to_air(block: Block, ruleset: RuleSet) -> tuple[Block, bool]:
    if block.id in ruleset.map_to_air_ids:
        return Block(id="minecraft:air", states={}, nbt=None), True
    return block, False


def normalize_variants(block: Block, ruleset: RuleSet) -> tuple[Block, bool]:
    target_id = ruleset.normalize_map.get(block.id)
    if target_id and target_id != block.id:
        return Block(id=target_id, states=dict(block.states), nbt=block.nbt), True
    return block, False
