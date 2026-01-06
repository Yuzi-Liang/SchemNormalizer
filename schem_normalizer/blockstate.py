from __future__ import annotations

def parse_block_state(block_state: str) -> tuple[str, dict[str, str]]:
    block_state = block_state.strip()
    if not block_state:
        raise ValueError("Empty block state string.")
    if "[" not in block_state:
        return block_state, {}
    base, rest = block_state.split("[", 1)
    if not rest.endswith("]"):
        raise ValueError(f"Invalid block state string: {block_state}")
    body = rest[:-1].strip()
    if not body:
        return base, {}
    states: dict[str, str] = {}
    for part in body.split(","):
        if "=" not in part:
            raise ValueError(f"Invalid block state entry: {part}")
        key, value = part.split("=", 1)
        states[key.strip()] = value.strip()
    return base, states


def format_block_state(block_id: str, states: dict[str, str]) -> str:
    if not states:
        return block_id
    parts = [f"{key}={states[key]}" for key in sorted(states)]
    return f"{block_id}[{','.join(parts)}]"
