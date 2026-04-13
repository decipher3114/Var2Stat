#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Any, Dict

import click
from fontTools.ttLib import TTFont

SCHEMA = "https://raw.githubusercontent.com/decipher3114/Var2Stat/refs/heads/main/schema.json"

WEIGHT_NAMES: Dict[int, str] = {
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


def is_hardcoded_italic(font: TTFont, family_name: str) -> bool:
    """Check if font is hardcoded italic (no ital axis but styled as italic)."""
    has_ital_axis = any(axis.axisTag == "ital" for axis in font["fvar"].axes)
    if has_ital_axis:
        return False

    family_name_italic = "italic" in family_name.lower()
    post_italic = "post" in font and font["post"].italicAngle != 0
    return family_name_italic or post_italic


def get_instance_name(
    coordinates: Dict[str, Any],
    index: int,
    hardcoded_italic: bool,
) -> str:
    """Generate descriptive variant name from instance coordinates."""
    if "wght" in coordinates:
        weight_value = coordinates["wght"]
        if weight_value in WEIGHT_NAMES:
            base_name = WEIGHT_NAMES[weight_value]
        else:
            closest = min(WEIGHT_NAMES.keys(), key=lambda x: abs(x - weight_value))
            base_name = f"{WEIGHT_NAMES[closest]}{int(weight_value)}"
    else:
        base_name = f"Instance{index + 1}"

    italic = hardcoded_italic or coordinates.get("ital") == 1
    return f"{base_name} Italic" if italic else base_name


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

        hardcoded_italic = is_hardcoded_italic(font, original_font_name)

        # Process axis defaults
        axes_defaults = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}

        # Process available instances
        variants = {}
        for i, instance in enumerate(font["fvar"].instances):
            coordinates = dict(instance.coordinates)
            instance_name = get_instance_name(coordinates, i, hardcoded_italic)
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
        "$schema": SCHEMA,
        "file": font_info["font_path"],
        "font_name": font_info["font_name"],
        "axes": global_axes,
        "variants": optimized_variants,
    }


@click.command("config")
@click.argument("font_file", type=str)
def config_command(font_file: str) -> None:
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
