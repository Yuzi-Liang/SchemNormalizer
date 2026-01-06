from __future__ import annotations

import argparse
from pathlib import Path

from .adapter import read_schematic, write_schematic
from .pipeline import apply_pipeline
from .rules import RuleError, load_rules


def _resolve_output_path(input_path: Path, output: Path | None) -> Path:
    if output is None:
        return input_path.with_suffix(".normalized.schem")
    if output.exists() and output.is_dir():
        return output / input_path.name
    return output


def _iter_input_files(input_path: Path, pattern: str) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return [path for path in input_path.rglob(pattern) if path.is_file()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize .schem blocks using JSON rules.")
    parser.add_argument("input", type=Path, help="Input .schem file or directory")
    parser.add_argument("-o", "--output", type=Path, help="Output file or directory")
    parser.add_argument("-c", "--config", type=Path, required=True, help="Rules JSON file")
    parser.add_argument("--glob", default="*.schem", help="Glob pattern for batch mode")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output files")
    args = parser.parse_args()

    try:
        ruleset = load_rules(args.config)
    except RuleError as exc:
        raise SystemExit(f"Rules error: {exc}")

    input_path = args.input
    if not input_path.exists():
        raise SystemExit("Input path does not exist.")

    if input_path.is_dir() and args.output is None:
        raise SystemExit("Output directory is required for batch mode.")

    files = _iter_input_files(input_path, args.glob)
    if not files:
        raise SystemExit("No .schem files matched the input.")

    for input_file in files:
        if input_path.is_file():
            output_file = _resolve_output_path(input_file, args.output)
        else:
            relative = input_file.relative_to(input_path)
            output_dir = args.output
            output_file = output_dir / relative
            output_file.parent.mkdir(parents=True, exist_ok=True)

        schematic = read_schematic(input_file)
        normalized, stats = apply_pipeline(schematic, ruleset)

        print(
            f"{input_file} -> {output_file} | "
            f"air: {stats.map_to_air}, normalized: {stats.normalize_variants}"
        )

        if not args.dry_run:
            write_schematic(normalized, output_file)


if __name__ == "__main__":
    main()
