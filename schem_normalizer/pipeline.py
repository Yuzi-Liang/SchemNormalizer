from __future__ import annotations

from .model import BlockPlacement, Schematic
from .rules import RuleSet
from .transforms import TransformStats, map_to_air, normalize_variants


TRANSFORMS = {
    "map_to_air": map_to_air,
    "normalize_variants": normalize_variants,
}


def apply_pipeline(schematic: Schematic, ruleset: RuleSet) -> tuple[Schematic, TransformStats]:
    stats = TransformStats()
    new_blocks: list[BlockPlacement] = []

    for placement in schematic.blocks:
        block = placement.block
        for name in ruleset.pipeline:
            if name == "map_to_air":
                block, changed = map_to_air(block, ruleset)
                if changed:
                    stats.map_to_air += 1
            elif name == "normalize_variants":
                block, changed = normalize_variants(block, ruleset)
                if changed:
                    stats.normalize_variants += 1
            else:
                raise ValueError(f"Unknown transform: {name}")
        new_blocks.append(BlockPlacement(pos=placement.pos, block=block))

    output = Schematic(
        size=schematic.size,
        blocks=new_blocks,
        data_version=schematic.data_version,
        version=schematic.version,
        metadata=dict(schematic.metadata),
    )
    return output, stats
