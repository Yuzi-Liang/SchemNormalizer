from __future__ import annotations

from .model import BlockPlacement, Schematic
from .rules import RuleSet
from .transforms import TransformStats, map_to_air, normalize_variants, strip_states


TRANSFORMS = {
    "map_to_air": map_to_air,
    "normalize_variants": normalize_variants,
    "strip_states": strip_states,
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
            elif name == "strip_states":
                before_states = bool(block.states)
                before_nbt = block.nbt is not None
                block, changed = strip_states(block, ruleset)
                if changed:
                    if before_states and not block.states:
                        stats.strip_states += 1
                    if before_nbt and block.nbt is None:
                        stats.strip_nbt += 1
            else:
                raise ValueError(f"Unknown transform: {name}")
        new_blocks.append(BlockPlacement(pos=placement.pos, block=block))

    output = Schematic(
        size=schematic.size,
        blocks=new_blocks,
        data_version=schematic.data_version,
        version=schematic.version,
        metadata=dict(schematic.metadata),
        container=schematic.container,
        blocks_container=schematic.blocks_container,
        block_data_key=schematic.block_data_key,
    )
    return output, stats
