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

## Normalize (apply rules)
Single file:
```
python -m schem_normalizer -c rules\example.json input.schem -o out_dir
```

Batch directory:
```
python -m schem_normalizer -c rules\example.json E:\input_dir -o E:\output_dir --glob "*.schem"
```

You can also use the explicit subcommand:
```
python -m schem_normalizer normalize -c rules\example.json input.schem -o out_dir
```

## Count blocks
Aggregated totals:
```
python -m schem_normalizer count E:\input_dir --glob "*.schem"
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

## Rules
Rules are defined in JSON. See `rules/example.json` for a complete template.
