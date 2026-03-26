# Var2Stat

Convert variable fonts to static font instances with configuration-based axis control.

## Features

- Extract axis information and generate optimized configuration files
- Smart axis inheritance (global defaults with variant overrides)
- True static output with all variation tables removed

## Installation

```bash
uv tool install var2stat
```

## Usage

- **Step 1**: Generate config from variable font (creates `<font_file>-config.json` in the same directory as the font):

  ```bash
  uvx var2stat config <font_file.ttf>
  ```

- **Step 2**: Generate static fonts from a config file:

  ```bash
  uvx var2stat generate <config_file.json>
  ```

  Output is always saved to a folder named after the canonicalized font name, with files named `<canonical_font_name>_<variant>.ttf`.

## Config Structure

```json
{
  "$schema": "https://raw.githubusercontent.com/decipher3114/Var2Stat/refs/heads/main/schema.json",
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
