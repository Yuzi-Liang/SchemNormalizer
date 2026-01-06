from __future__ import annotations

from pathlib import Path

import nbtlib
from nbtlib import ByteArray, Compound, Int, IntArray, List, Short

from .blockstate import format_block_state, parse_block_state
from .model import Block, BlockPlacement, Schematic


def read_schematic(path: Path) -> Schematic:
    root = nbtlib.load(str(path))

    container = root
    container_kind = "root"
    if isinstance(root.get("Schematic"), Compound):
        container = root["Schematic"]
        container_kind = "schematic"

    blocks_container = container
    blocks_container_kind = "root"
    if isinstance(container.get("Blocks"), Compound):
        blocks_container = container["Blocks"]
        blocks_container_kind = "blocks"

    width = int(container.get("Width", 0))
    height = int(container.get("Height", 0))
    length = int(container.get("Length", 0))
    if width <= 0 or height <= 0 or length <= 0:
        raise ValueError("Invalid schematic dimensions.")

    palette = blocks_container.get("Palette")
    if palette is None:
        raise ValueError("Schematic is missing Palette tag.")

    palette_by_id: dict[int, str] = {}
    for name, value in palette.items():
        palette_by_id[int(value)] = str(name)

    raw_block_data = blocks_container.get("BlockData")
    block_data_key = "BlockData"
    if raw_block_data is None:
        raw_block_data = blocks_container.get("Data")
        block_data_key = "Data"
    if raw_block_data is None:
        raise ValueError("Schematic is missing BlockData/Data tag.")
    block_data = _decode_varints(bytes(raw_block_data), width * height * length)

    block_entities = _read_block_entities(blocks_container)

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

    metadata = _collect_metadata(container)
    return Schematic(
        size=size,
        blocks=blocks,
        data_version=_maybe_int(container.get("DataVersion")),
        version=_maybe_int(container.get("Version")),
        metadata=metadata,
        container=container_kind,
        blocks_container=blocks_container_kind,
        block_data_key=block_data_key,
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

    root = Compound()
    if schematic.container == "schematic":
        container = Compound()
        root["Schematic"] = container
    else:
        container = root

    if schematic.blocks_container == "blocks":
        blocks_container = Compound()
        container["Blocks"] = blocks_container
    else:
        blocks_container = container

    for key, value in schematic.metadata.items():
        container[key] = value

    container["Version"] = Int(schematic.version or 2)
    if schematic.data_version is not None:
        container["DataVersion"] = Int(schematic.data_version)
    container["Width"] = Short(width)
    container["Height"] = Short(height)
    container["Length"] = Short(length)

    blocks_container["PaletteMax"] = Int(len(palette))
    blocks_container["Palette"] = palette_compound
    blocks_container[schematic.block_data_key] = ByteArray(_to_signed_bytes(_encode_varints(block_data)))
    blocks_container["BlockEntities"] = List[Compound](block_entities)

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


def _to_signed_bytes(data: bytes) -> list[int]:
    signed: list[int] = []
    for byte in data:
        signed.append(byte - 256 if byte > 127 else byte)
    return signed


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
        "Data",
        "BlockEntities",
        "TileEntities",
        "Blocks",
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
