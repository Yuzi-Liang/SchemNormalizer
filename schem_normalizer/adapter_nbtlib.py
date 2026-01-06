from __future__ import annotations

from pathlib import Path

import nbtlib
from nbtlib import ByteArray, Compound, Int, IntArray, List, Short

from .blockstate import format_block_state, parse_block_state
from .model import Block, BlockPlacement, Schematic


def read_schematic(path: Path) -> Schematic:
    root = nbtlib.load(str(path))

    width = int(root.get("Width", 0))
    height = int(root.get("Height", 0))
    length = int(root.get("Length", 0))
    if width <= 0 or height <= 0 or length <= 0:
        raise ValueError("Invalid schematic dimensions.")

    palette = root.get("Palette")
    if palette is None:
        raise ValueError("Schematic is missing Palette tag.")

    palette_by_id: dict[int, str] = {}
    for name, value in palette.items():
        palette_by_id[int(value)] = str(name)

    raw_block_data = root.get("BlockData")
    if raw_block_data is None:
        raise ValueError("Schematic is missing BlockData tag.")
    block_data = _decode_varints(bytes(raw_block_data), width * height * length)

    block_entities = _read_block_entities(root)

    blocks: list[BlockPlacement] = []
    size = (width, height, length)
    for x in range(width):
        for z in range(length):
            for y in range(height):
                index = _index(x, y, z, size)
                palette_index = block_data[index]
                block_state = palette_by_id.get(palette_index)
                if block_state is None:
                    raise ValueError(f"Missing palette entry for index {palette_index}.")
                block_id, states = parse_block_state(block_state)
                nbt = block_entities.get((x, y, z))
                blocks.append(
                    BlockPlacement(
                        pos=(x, y, z),
                        block=Block(id=block_id, states=states, nbt=nbt),
                    )
                )

    metadata = _collect_metadata(root)
    return Schematic(
        size=size,
        blocks=blocks,
        data_version=_maybe_int(root.get("DataVersion")),
        version=_maybe_int(root.get("Version")),
        metadata=metadata,
    )


def write_schematic(schematic: Schematic, path: Path) -> None:
    width, height, length = schematic.size
    if width <= 0 or height <= 0 or length <= 0:
        raise ValueError("Invalid schematic dimensions.")

    palette: dict[str, int] = {}
    palette_list: list[str] = []

    block_data = [0] * (width * height * length)
    for placement in schematic.blocks:
        x, y, z = placement.pos
        block_state = format_block_state(placement.block.id, placement.block.states)
        if block_state not in palette:
            palette[block_state] = len(palette_list)
            palette_list.append(block_state)
        index = _index(x, y, z, schematic.size)
        block_data[index] = palette[block_state]

    palette_compound = Compound({name: Int(value) for name, value in palette.items()})

    block_entities = _build_block_entities(schematic)

    root = Compound(dict(schematic.metadata))
    root["Version"] = Int(schematic.version or 2)
    if schematic.data_version is not None:
        root["DataVersion"] = Int(schematic.data_version)
    root["Width"] = Short(width)
    root["Height"] = Short(height)
    root["Length"] = Short(length)
    root["PaletteMax"] = Int(len(palette))
    root["Palette"] = palette_compound
    root["BlockData"] = ByteArray(list(_encode_varints(block_data)))
    root["BlockEntities"] = List[Compound](block_entities)

    nbtlib.File(root).save(str(path), gzipped=True)


def _index(x: int, y: int, z: int, size: tuple[int, int, int]) -> int:
    width, height, length = size
    return y + (z * height) + (x * height * length)


def _decode_varints(data: bytes, count: int | None = None) -> list[int]:
    values: list[int] = []
    value = 0
    shift = 0
    for byte in data:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            if shift > 35:
                raise ValueError("VarInt is too long.")
            continue
        values.append(value)
        if count is not None and len(values) >= count:
            return values
        value = 0
        shift = 0
    if shift != 0:
        raise ValueError("Truncated VarInt sequence.")
    if count is not None and len(values) != count:
        raise ValueError("BlockData length does not match volume.")
    return values


def _encode_varints(values: list[int]) -> bytes:
    out = bytearray()
    for value in values:
        if value < 0:
            raise ValueError("Negative palette index not allowed.")
        remaining = value
        while True:
            byte = remaining & 0x7F
            remaining >>= 7
            if remaining:
                out.append(byte | 0x80)
            else:
                out.append(byte)
                break
    return bytes(out)


def _read_block_entities(root: Compound) -> dict[tuple[int, int, int], Compound]:
    entities = root.get("BlockEntities") or root.get("TileEntities") or []
    mapping: dict[tuple[int, int, int], Compound] = {}
    for entity in entities:
        pos = None
        if "Pos" in entity:
            pos = tuple(int(value) for value in entity["Pos"])
        elif all(k in entity for k in ("x", "y", "z")):
            pos = (int(entity["x"]), int(entity["y"]), int(entity["z"]))
        if pos is None:
            continue
        mapping[pos] = entity.copy()
    return mapping


def _build_block_entities(schematic: Schematic) -> list[Compound]:
    entities: list[Compound] = []
    for placement in schematic.blocks:
        if placement.block.nbt is None:
            continue
        if placement.block.id == "minecraft:air":
            continue
        entity = placement.block.nbt
        if isinstance(entity, Compound):
            entity = entity.copy()
        else:
            entity = Compound(entity)
        entity["Pos"] = IntArray([placement.pos[0], placement.pos[1], placement.pos[2]])
        entities.append(entity)
    return entities


def _collect_metadata(root: Compound) -> dict:
    known = {
        "Version",
        "DataVersion",
        "Width",
        "Height",
        "Length",
        "PaletteMax",
        "Palette",
        "BlockData",
        "BlockEntities",
        "TileEntities",
    }
    metadata = {}
    for key, value in root.items():
        if key not in known:
            metadata[key] = value
    return metadata


def _maybe_int(value) -> int | None:
    if value is None:
        return None
    return int(value)
