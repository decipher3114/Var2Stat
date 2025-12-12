#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Dict, Any

import click
from fontTools.ttLib import TTFont

SCHEMA = "schema.json"


def extract_font_info(font_path: str) -> Dict[str, Any]:
    font_path_obj = Path(font_path).resolve()
    if not font_path_obj.exists():
        raise FileNotFoundError(f"Font file '{font_path}' not found")

    font = TTFont(font_path)
    print(f"[INFO]: Font file loaded: {font_path_obj.name}")

    try:
        if "fvar" not in font:
            raise ValueError("This is not a variable font (missing fvar table)")

        # Extract original font family name
        original_font_name = None
        for record in font["name"].names:
            if record.nameID == 1 and record.platformID == 3 and record.platEncID == 1:
                original_font_name = record.toUnicode()
                break

        if not original_font_name:
            original_font_name = font_path_obj.stem

        # Process axis defaults
        axes_defaults = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}

        # Process available instances
        variants = {}
        weight_names = {
            100: "Thin",
            200: "ExtraLight",
            300: "Light",
            400: "Regular",
            500: "Medium",
            600: "SemiBold",
            700: "Bold",
            800: "ExtraBold",
            900: "Black",
        }

        for i, instance in enumerate(font["fvar"].instances):
            coordinates = dict(instance.coordinates)

            # Generate descriptive name from weight
            if "wght" in coordinates:
                weight_value = coordinates["wght"]
                if weight_value in weight_names:
                    instance_name = weight_names[weight_value]
                else:
                    closest = min(
                        weight_names.keys(), key=lambda x: abs(x - weight_value)
                    )
                    instance_name = f"{weight_names[closest]}{int(weight_value)}"
            else:
                instance_name = f"Instance{i + 1}"

            variants[instance_name] = coordinates

        return {
            "font_path": str(font_path_obj),
            "font_name": original_font_name,
            "axes_defaults": axes_defaults,
            "variants": variants,
        }

    finally:
        font.close()


def create_config_structure(font_info: Dict[str, Any]) -> Dict[str, Any]:
    variants = font_info["variants"]
    available_axes = list(font_info["axes_defaults"].keys())

    # Analyze common parameters across instances
    global_axes = {}
    for axis_tag in available_axes:
        axis_values = [
            variant_axes.get(axis_tag)
            for variant_axes in variants.values()
            if axis_tag in variant_axes
        ]

        # Set global value if all instances have the same value
        if axis_values and all(val == axis_values[0] for val in axis_values):
            global_axes[axis_tag] = axis_values[0]
        else:
            global_axes[axis_tag] = None

    # Build instance-specific configurations
    optimized_variants = {}
    for variant_name, variant_axes in variants.items():
        optimized_variant = {
            axis_tag: value
            for axis_tag, value in variant_axes.items()
            if global_axes.get(axis_tag) != value
        }
        optimized_variants[variant_name] = optimized_variant

    return {
        "$schema": f"./{SCHEMA}",
        "file": font_info["font_path"],
        "font_name": font_info["font_name"],
        "axes": global_axes,
        "variants": optimized_variants,
    }


@click.command()
@click.argument("font_file", type=str)
def main(font_file: str) -> None:
    """Generate configuration file for variable font.

    FONT_FILE: Path to the variable font file (.ttf or .otf)
    """
    try:
        font_info = extract_font_info(font_file)
        config = create_config_structure(font_info)

        config_file = Path(font_file).stem + "-config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        print(f"[INFO]: Configuration saved to: {config_file}")

    except KeyboardInterrupt:
        print("\n[INFO]: Config generation interrupted by user")
        raise click.Abort()
    except Exception as e:
        print(f"[ERROR]: {e}")
        raise click.Abort()


if __name__ == "__main__":
    main()
