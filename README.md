# SchemNormalizer

Normalize Minecraft `.schem` files with JSON rules and count block usage.  
Supports WorldEdit `.schem` variants and preserves block states and NBT.

## Features
- Map specific blocks to air.
- Normalize block variants to a single target block.
- Preserve block states and block entity NBT.
- Support two `.schem` layouts:
  - Top-level `Palette` + `BlockData`
  - Nested `Schematic/Blocks/Data`
- Count blocks in a single file or a directory.

## Install
```
pip install -r requirements.txt
```

## Go wrapper (optional)
Build a small executable that calls the Python module:
```
go build -o schem_normalizer .\cmd\schem_normalizer
```

Run it like:
```
.\schem_normalizer -c rules\example.json input.schem -o out_dir
```

You can override which Python is used with `SCHEM_NORMALIZER_PYTHON`.
This wrapper uses Cobra for CLI help and argument handling.
If `-c/--config` is omitted, it will use `rules/example.json` when present.

## Normalize (apply rules)
Single file:
```
python -m schem_normalizer -c rules\example.json input.schem -o out_dir
```

Batch directory:
```
python -m schem_normalizer -c rules\example.json path\to\input_dir -o path\to\output_dir --glob "*.schem"
```

You can also use the explicit subcommand:
```
python -m schem_normalizer normalize -c rules\example.json input.schem -o out_dir
```
Short alias:
```
python -m schem_normalizer n -c rules\example.json input.schem -o path\to\output_dir
```

## Count blocks
Aggregated totals:
```
python -m schem_normalizer count path\to\input_dir --glob "*.schem"
```
Short alias:
```
python -m schem_normalizer c path\to\input_dir
```
Default glob (no --glob needed):
```
python -m schem_normalizer count path\to\input_dir
```

Per file:
```
python -m schem_normalizer count E:\input_dir --glob "*.schem" --per-file
```

By blockstate:
```
python -m schem_normalizer count input.schem --by-state
```

Disable progress:
```
python -m schem_normalizer count E:\input_dir --no-progress
```

## Sizes
Print dimensions for each file:
```
python -m schem_normalizer size path\to\input_dir --glob "*.schem"
```
Short alias:
```
python -m schem_normalizer s path\to\input_dir
```

Summary mode (max edge threshold, default 32):
```
python -m schem_normalizer size path\to\input_dir --glob "*.schem" --threshold 32 --summary
```

Export matching files:
```
python -m schem_normalizer size path\to\input_dir --glob "*.schem" --threshold 32 --export path\to\output_dir --select within
```

## Rules
Rules are defined in JSON. See `rules/example.json` for a complete template.

Rule options you can use:
- `normalize_defaults.preserve_states`: default state preservation for normalize rules.
- `normalize_defaults.preserve_nbt`: default NBT preservation for normalize rules.
- `strip_states.ids`: clear block states for specific ids after normalization.
- `strip_nbt.ids`: clear block entity NBT for specific ids after normalization.

Notes:
- Mapping to air always drops states and NBT.
- `strip_states` runs after `normalize_variants` when listed in `pipeline`.
