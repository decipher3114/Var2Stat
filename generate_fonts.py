#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import click
import jsonschema
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

SCHEMA = "schema.json"


def load_config(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        print(f"[INFO]: Config file loaded: {Path(config_path).name}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON syntax at line {e.lineno}, column {e.colno}")

    # Validate against schema if available
    if os.path.exists(SCHEMA):
        try:
            with open(SCHEMA, "r", encoding="utf-8") as f:
                schema = json.load(f)
            jsonschema.validate(config_data, schema)
            print("[INFO]: Config validated")
        except jsonschema.ValidationError as e:
            error_msg = e.message
            if e.absolute_path:
                path_str = " -> ".join(str(p) for p in e.absolute_path)
                error_msg += f" at {path_str}"
            raise ValueError(error_msg)

    return config_data


def remove_variation_tables(font: TTFont) -> None:
    # Remove variable font tables to create static font
    variation_tables = ["fvar", "avar", "gvar", "cvar", "HVAR", "VVAR", "MVAR", "STAT"]

    for table in variation_tables:
        if table in font:
            del font[table]


def update_font_names(
    font: TTFont, font_name: str, variant_name: str, axes: Dict[str, Union[int, float]]
) -> None:
    # Update font metadata and naming information
    name_table = font["name"]
    weight_value = axes.get("wght", 400)

    for record in name_table.names:
        if record.platformID == 3 and record.platEncID == 1:
            if record.nameID == 1:  # Family name
                record.string = font_name.encode("utf-16-be")
            elif record.nameID == 2:  # Subfamily name
                record.string = variant_name.encode("utf-16-be")
            elif record.nameID == 4:  # Full name
                full_name = (
                    font_name
                    if variant_name == "Regular"
                    else f"{font_name} {variant_name}"
                )
                record.string = full_name.encode("utf-16-be")
            elif record.nameID == 6:  # PostScript name
                ps_name = f"{font_name.replace(' ', '')}-{variant_name}"
                record.string = ps_name.encode("utf-16-be")

    # Update OS/2 weight class
    if "OS/2" in font:
        font["OS/2"].usWeightClass = int(weight_value)

    # Update head table macStyle for bold
    if "head" in font:
        if weight_value >= 700:
            font["head"].macStyle |= 0x01
        else:
            font["head"].macStyle &= ~0x01


def extract_font_info(font: TTFont) -> tuple[Dict[str, float], str]:
    # Extract axis defaults and original font name from variable font
    if "fvar" not in font:
        raise ValueError("Not a variable font (missing fvar table)")

    if "name" not in font:
        raise ValueError("Font missing name table")

    # Extract axis defaults
    font_defaults = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}

    # Extract original font family name
    for record in font["name"].names:
        if record.nameID == 1 and record.platformID == 3 and record.platEncID == 1:
            return font_defaults, record.toUnicode()

    raise ValueError("Could not extract font family name from font file")


def generate_variant(
    font: TTFont,
    font_name: str,
    variant_name: str,
    variant_config: Dict[str, Union[int, float]],
    global_axes: Dict[str, Optional[Union[int, float]]],
    font_defaults: Dict[str, float],
    output_folder: str,
) -> bool:
    # Generate a single static font variant
    try:
        # Merge global and variant axes
        merged_axes = global_axes.copy()
        merged_axes.update(variant_config)

        # Resolve axis values
        resolved_axes = {
            axis: font_defaults[axis] if value is None else value
            for axis, value in merged_axes.items()
            if axis in font_defaults
        }

        # Display variant info
        axis_parts = [f"'{axis}'={value}" for axis, value in resolved_axes.items()]
        print(f'- Variant: "{variant_name}", Axes: [{", ".join(axis_parts)}]')

        # Generate static font
        static_font = instancer.instantiateVariableFont(font, resolved_axes)
        remove_variation_tables(static_font)
        update_font_names(static_font, font_name, variant_name, resolved_axes)

        # Save font
        output_filename = f"{font_name.replace(' ', '')}-{variant_name}.ttf"
        static_font.save(os.path.join(output_folder, output_filename))

        return True

    except Exception as e:
        print(f"[ERROR]: Failed to generate {variant_name}: {e}")
        return False


def generate_from_config(config_path: str, output_dir: str = "output") -> None:
    # Process configuration and generate static font files
    config = load_config(config_path)

    font_file = config["file"]
    font_name = config["font_name"]

    print("[INFO]: Font Info:")

    if not os.path.exists(font_file):
        raise FileNotFoundError(f"Font file '{font_file}' not found")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load and validate font
    font = TTFont(font_file)
    try:
        font_defaults, original_font_name = extract_font_info(font)

        # Use config font name or fallback to original
        if not font_name:
            font_name = original_font_name

        # Display font information
        if original_font_name == font_name:
            print(f'- Font Name: "{font_name}"')
        else:
            print(f'- Original Font Name: "{original_font_name}"')
            print(f'- Target Font Name: "{font_name}"')
        print(f"- Available Axes: {list(font_defaults.keys())}")

        print("[INFO]: Variants:")

        # Generate all variants
        success_count = 0
        for variant_name, variant_config in config["variants"].items():
            if generate_variant(
                font,
                font_name,
                variant_name,
                variant_config,
                config["axes"],
                font_defaults,
                output_dir,
            ):
                success_count += 1

        print(f"[INFO]: Generated {success_count}/{len(config['variants'])} variants")
        print(f"[INFO]: Static font files saved to '{output_dir}' directory")

    finally:
        font.close()


@click.command()
@click.argument("config", type=str)
@click.option(
    "--output",
    "-o",
    default="output",
    help="Output directory for generated fonts (default: output)",
)
def main(config: str, output: str) -> None:
    """Generate static fonts from variable fonts.

    CONFIG: Configuration file path (required)
    """
    try:
        generate_from_config(config, output)
    except KeyboardInterrupt:
        print("\n[INFO]: Generation interrupted by user")
        raise click.Abort()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR]: {e}")
        print("[INFO]: Generate config using: uv run dump_config.py <font_file.ttf>")
        raise click.Abort()
    except Exception as e:
        print(f"[ERROR]: Generation failed: {e}")
        raise click.Abort()


if __name__ == "__main__":
    main()
