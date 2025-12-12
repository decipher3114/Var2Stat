# Var2Stat

Convert variable fonts to static font instances with configuration-based axis control.

## Features

- Extract axis information and generate optimized configuration files
- Smart axis inheritance (global defaults with variant overrides)
- True static output with all variation tables removed

## Usage

- **Step 1**: Generate config from variable font (creates `{FontName}-config.json`):

  ```bash
  uv run dump_config.py <font_file.ttf>
  ```

- **Step 2**: Generate static fonts:

  ```bash
  uv run generate_fonts.py <config_file.json>
  ```

  Optional: Specify output directory with `--output` or `-o`

  ```bash
  uv run generate_fonts.py <config_file.json> --output fonts
  ```

## Config Structure

```json
{
  "file": "font.ttf",
  "font_name": "Font Name",
  "axes": { "wght": null, "opsz": 16 },
  "variants": {
    "Regular": { "wght": 400 },
    "Bold": { "wght": 700 }
  }
}
```

- Global axes with `null` use font defaults
- Variant axes override global values
- Output saved to `output/` directory (or specified directory)
