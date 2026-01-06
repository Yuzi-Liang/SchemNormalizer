from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Block:
    id: str
    states: dict[str, str] = field(default_factory=dict)
    nbt: Any | None = None


@dataclass
class BlockPlacement:
    pos: tuple[int, int, int]
    block: Block


@dataclass
class Schematic:
    size: tuple[int, int, int]
    blocks: list[BlockPlacement]
    data_version: int | None = None
    version: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
