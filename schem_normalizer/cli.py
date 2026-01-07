from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
import shutil

from .adapter import read_schematic, write_schematic
from .blockstate import format_block_state
from .pipeline import apply_pipeline
from .rules import RuleError, load_rules

_PROGRESS_ENABLED = True


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


def _count_blocks(
    input_path: Path,
    pattern: str,
    by_state: bool,
    per_file: bool,
    show_progress: bool,
) -> None:
    files = _iter_input_files(input_path, pattern)
    if not files:
        raise SystemExit("No .schem files matched the input.")

    totals: Counter[str] = Counter()
    total_files = len(files)
    for index, input_file in enumerate(files, start=1):
        try:
            schematic = read_schematic(input_file)
        except Exception as exc:
            if show_progress:
                _print_progress(f"[{index}/{total_files}] {input_file} | error")
            print(f"skip {input_file}: {exc}", file=sys.stderr)
            continue
        counter: Counter[str] = Counter()
        block_count = len(schematic.blocks)
        for i, placement in enumerate(schematic.blocks, start=1):
            if by_state:
                key = format_block_state(placement.block.id, placement.block.states)
            else:
                key = placement.block.id
            counter[key] += 1
            if show_progress and block_count >= 50000 and i % 10000 == 0:
                _print_progress(
                    f"[{index}/{total_files}] {input_file} | blocks {i}/{block_count}"
                )
        if per_file:
            print(f"[{input_file}]")
            for key in sorted(counter):
                print(f"{key}:{counter[key]}")
        totals.update(counter)
        if show_progress:
            _print_progress(f"[{index}/{total_files}] {input_file} | done")

    if not per_file:
        for key in sorted(totals):
            print(f"{key}:{totals[key]}")
    if show_progress and _PROGRESS_ENABLED:
        sys.stdout.write("\n")
        sys.stdout.flush()


def _print_sizes(
    input_path: Path,
    pattern: str,
    show_progress: bool,
    threshold: int,
    summary_only: bool,
    export_dir: Path | None,
    export_select: str,
) -> None:
    files = _iter_input_files(input_path, pattern)
    if not files:
        raise SystemExit("No .schem files matched the input.")

    total_files = len(files)
    over = 0
    within = 0
    if export_dir is not None:
        export_dir.mkdir(parents=True, exist_ok=True)
    for index, input_file in enumerate(files, start=1):
        try:
            schematic = read_schematic(input_file)
        except Exception as exc:
            if show_progress:
                _print_progress(f"[{index}/{total_files}] {input_file} | error")
            print(f"skip {input_file}: {exc}", file=sys.stderr)
            continue

        width, height, length = schematic.size
        if show_progress:
            _print_progress(f"[{index}/{total_files}] {input_file} | done")
        max_edge = max(width, height, length)
        is_over = max_edge > threshold
        if is_over:
            over += 1
        else:
            within += 1
        if export_dir is not None:
            if (export_select == "over" and is_over) or (export_select == "within" and not is_over):
                shutil.copy2(input_file, export_dir / input_file.name)
        if not summary_only:
            print(f"{input_file}: {width}x{height}x{length}")

    if show_progress and _PROGRESS_ENABLED:
        sys.stdout.write("\n")
        sys.stdout.flush()
    print(f"over_{threshold}: {over}")
    print(f"within_{threshold}: {within}")


def _normalize(args: argparse.Namespace) -> None:
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

        try:
            schematic = read_schematic(input_file)
            normalized, stats = apply_pipeline(schematic, ruleset)
        except Exception as exc:
            print(f"skip {input_file}: {exc}", file=sys.stderr)
            continue

        print(
            f"{input_file} -> {output_file} | "
            f"air: {stats.map_to_air}, normalized: {stats.normalize_variants}"
        )

        if not args.dry_run:
            write_schematic(normalized, output_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize .schem blocks using JSON rules.")
    subparsers = parser.add_subparsers(dest="command")

    normalize_parser = subparsers.add_parser("normalize", help="Apply normalization rules")
    normalize_parser.add_argument("input", type=Path, help="Input .schem file or directory")
    normalize_parser.add_argument("-o", "--output", type=Path, help="Output file or directory")
    normalize_parser.add_argument("-c", "--config", type=Path, required=True, help="Rules JSON file")
    normalize_parser.add_argument("--glob", default="*.schem", help="Glob pattern for batch mode")
    normalize_parser.add_argument("--dry-run", action="store_true", help="Do not write output files")
    normalize_parser.set_defaults(func=_normalize)

    count_parser = subparsers.add_parser("count", help="Count blocks in schematics")
    count_parser.add_argument("input", type=Path, help="Input .schem file or directory")
    count_parser.add_argument("--glob", default="*.schem", help="Glob pattern for batch mode")
    count_parser.add_argument("--by-state", action="store_true", help="Count by blockstate")
    count_parser.add_argument(
        "--per-file",
        action="store_true",
        help="Print per-file counts instead of aggregated totals",
    )
    count_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the single-line progress indicator",
    )
    count_parser.set_defaults(func=_count_blocks)

    size_parser = subparsers.add_parser("size", help="Print schematic dimensions")
    size_parser.add_argument("input", type=Path, help="Input .schem file or directory")
    size_parser.add_argument("--glob", default="*.schem", help="Glob pattern for batch mode")
    size_parser.add_argument(
        "--threshold",
        type=int,
        default=32,
        help="Max edge length threshold for summary counts",
    )
    size_parser.add_argument(
        "--summary",
        action="store_true",
        help="Only print summary counts",
    )
    size_parser.add_argument(
        "--export",
        type=Path,
        help="Copy matching schematics to this directory",
    )
    size_parser.add_argument(
        "--select",
        choices=["within", "over"],
        default="within",
        help="Which size class to export (default: within)",
    )
    size_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the single-line progress indicator",
    )
    size_parser.set_defaults(func=_print_sizes)

    argv = sys.argv[1:]
    if argv and argv[0] not in ("normalize", "count", "size", "-h", "--help"):
        argv = ["normalize"] + argv
    args = parser.parse_args(argv)

    if args.command is None:
        if hasattr(args, "config"):
            _normalize(args)
        else:
            parser.print_help()
        return

    if args.command == "count":
        _count_blocks(
            args.input,
            args.glob,
            args.by_state,
            args.per_file,
            not args.no_progress,
        )
    elif args.command == "size":
        _print_sizes(
            args.input,
            args.glob,
            not args.no_progress,
            args.threshold,
            args.summary,
            args.export,
            args.select,
        )
    else:
        args.func(args)


def _print_progress(message: str) -> None:
    global _PROGRESS_ENABLED
    if not _PROGRESS_ENABLED:
        return
    padded = message.ljust(120)
    try:
        sys.stdout.write(f"\r{padded}")
        sys.stdout.flush()
    except OSError:
        _PROGRESS_ENABLED = False


if __name__ == "__main__":
    main()
