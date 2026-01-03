#!/usr/bin/env python3
"""
LED Position Calculator for Physical Lamp Marking

This script calculates which LEDs light up at specific wave heights and wind speeds,
so you can physically mark those positions on the lamp with labels/stickers.

Usage:
    python calculate_led_markers.py

Output:
    - LED positions for 1m, 2m, 3m wave heights
    - LED positions for 10, 20, 30 knots wind speeds
    - Physical LED indices you can mark on the lamp
"""

import re
import sys
from pathlib import Path


def parse_config_h(config_path):
    """Parse Config.h to extract lamp configuration."""
    with open(config_path, 'r') as f:
        content = f.read()

    # Extract configuration values using regex
    config = {}

    # LED strip mapping
    config['WAVE_HEIGHT_BOTTOM'] = int(re.search(r'#define WAVE_HEIGHT_BOTTOM\s+(\d+)', content).group(1))
    config['WAVE_HEIGHT_TOP'] = int(re.search(r'#define WAVE_HEIGHT_TOP\s+(\d+)', content).group(1))
    config['WIND_SPEED_BOTTOM'] = int(re.search(r'#define WIND_SPEED_BOTTOM\s+(\d+)', content).group(1))
    config['WIND_SPEED_TOP'] = int(re.search(r'#define WIND_SPEED_TOP\s+(\d+)', content).group(1))
    config['WAVE_PERIOD_BOTTOM'] = int(re.search(r'#define WAVE_PERIOD_BOTTOM\s+(\d+)', content).group(1))
    config['WAVE_PERIOD_TOP'] = int(re.search(r'#define WAVE_PERIOD_TOP\s+(\d+)', content).group(1))

    # Scaling parameters
    config['MAX_WAVE_HEIGHT_METERS'] = float(re.search(r'#define MAX_WAVE_HEIGHT_METERS\s+([\d.]+)', content).group(1))
    config['MAX_WIND_SPEED_MPS'] = float(re.search(r'#define MAX_WIND_SPEED_MPS\s+([\d.]+)', content).group(1))

    # Arduino ID
    config['ARDUINO_ID'] = int(re.search(r'const int ARDUINO_ID\s*=\s*(\d+)', content).group(1))

    # Calculate strip lengths and directions
    config['WAVE_HEIGHT_LENGTH'] = abs(config['WAVE_HEIGHT_TOP'] - config['WAVE_HEIGHT_BOTTOM']) + 1
    config['WIND_SPEED_LENGTH'] = abs(config['WIND_SPEED_TOP'] - config['WIND_SPEED_BOTTOM']) + 1
    config['WAVE_PERIOD_LENGTH'] = abs(config['WAVE_PERIOD_TOP'] - config['WAVE_PERIOD_BOTTOM']) + 1

    config['WAVE_HEIGHT_FORWARD'] = config['WAVE_HEIGHT_BOTTOM'] < config['WAVE_HEIGHT_TOP']
    config['WIND_SPEED_FORWARD'] = config['WIND_SPEED_BOTTOM'] < config['WIND_SPEED_TOP']

    return config


def calculate_wave_height_leds(wave_height_m, config):
    """
    Calculate how many LEDs light up for given wave height.
    Matches Arduino formula: numLEDs = (wave_height_m / MAX_WAVE_HEIGHT_METERS) * WAVE_HEIGHT_LENGTH
    """
    max_height = config['MAX_WAVE_HEIGHT_METERS']
    strip_length = config['WAVE_HEIGHT_LENGTH']

    # Arduino calculation
    num_leds = int((wave_height_m / max_height) * strip_length)

    # Constrain to strip length (Arduino does this too)
    num_leds = max(0, min(num_leds, strip_length))

    # Calculate physical LED indices
    bottom = config['WAVE_HEIGHT_BOTTOM']
    forward = config['WAVE_HEIGHT_FORWARD']

    lit_leds = []
    for i in range(num_leds):
        if forward:
            led_index = bottom + i
        else:
            led_index = bottom - i
        lit_leds.append(led_index)

    return num_leds, lit_leds


def calculate_wind_speed_leds(wind_speed_knots, config):
    """
    Calculate how many LEDs light up for given wind speed.
    Converts knots → m/s, then matches Arduino formula.

    Note: Wind strip has status LED at bottom and direction LED at top,
    so usable LEDs = WIND_SPEED_LENGTH - 2
    """
    # Convert knots to m/s (1 knot = 0.514444 m/s)
    wind_speed_mps = wind_speed_knots * 0.514444

    max_wind = config['MAX_WIND_SPEED_MPS']
    strip_length = config['WIND_SPEED_LENGTH']

    # Usable LEDs (excluding status and direction LEDs)
    usable_length = strip_length - 2

    # Arduino calculation
    num_leds = int((wind_speed_mps / max_wind) * usable_length)

    # Constrain to usable length
    num_leds = max(0, min(num_leds, usable_length))

    # Calculate physical LED indices
    # Wind strip: bottom LED = status, top LED = direction
    # Data LEDs start from bottom+1 (or bottom-1 if reversed)
    bottom = config['WIND_SPEED_BOTTOM']
    forward = config['WIND_SPEED_FORWARD']

    lit_leds = []
    for i in range(num_leds):
        if forward:
            led_index = bottom + 1 + i  # Skip status LED at bottom
        else:
            led_index = bottom - 1 - i  # Skip status LED at bottom
        lit_leds.append(led_index)

    return num_leds, lit_leds, wind_speed_mps


def print_header(config):
    """Print lamp configuration header."""
    print("=" * 70)
    print(f"LED MARKER CALCULATOR - Lamp {config['ARDUINO_ID']}")
    print("=" * 70)
    print()
    print("CONFIGURATION:")
    print(f"  Wave Height Strip: LED {config['WAVE_HEIGHT_BOTTOM']} → {config['WAVE_HEIGHT_TOP']} ({config['WAVE_HEIGHT_LENGTH']} LEDs)")
    print(f"  Wind Speed Strip:  LED {config['WIND_SPEED_BOTTOM']} → {config['WIND_SPEED_TOP']} ({config['WIND_SPEED_LENGTH']} LEDs)")
    print(f"  Wave Period Strip: LED {config['WAVE_PERIOD_BOTTOM']} → {config['WAVE_PERIOD_TOP']} ({config['WAVE_PERIOD_LENGTH']} LEDs)")
    print()
    print(f"  Max Wave Height: {config['MAX_WAVE_HEIGHT_METERS']} meters")
    print(f"  Max Wind Speed:  {config['MAX_WIND_SPEED_MPS']} m/s (~{config['MAX_WIND_SPEED_MPS'] / 0.514444:.1f} knots)")
    print()
    print("=" * 70)
    print()


def print_wave_height_markers(config):
    """Print wave height LED positions for 1m, 2m, 3m."""
    print("WAVE HEIGHT MARKERS (Right Strip)")
    print("-" * 70)
    print()

    for height_m in [1.0, 2.0, 3.0]:
        num_leds, lit_leds = calculate_wave_height_leds(height_m, config)

        if num_leds == 0:
            print(f"  {height_m}m → No LEDs (below minimum)")
        elif num_leds >= config['WAVE_HEIGHT_LENGTH']:
            print(f"  {height_m}m → ALL {num_leds} LEDs (maximum)")
        else:
            # Find the topmost lit LED (the marker position)
            marker_led = lit_leds[-1] if lit_leds else None
            print(f"  {height_m}m → {num_leds} LEDs lit → Mark at LED #{marker_led}")

        # Show all lit LED indices for reference
        if lit_leds:
            print(f"         Lit LEDs: {lit_leds}")
        print()


def print_wind_speed_markers(config):
    """Print wind speed LED positions for 10, 20, 30 knots."""
    print("WIND SPEED MARKERS (Center Strip)")
    print("-" * 70)
    print()
    print("NOTE: Wind strip has 2 special LEDs:")
    print(f"  - LED #{config['WIND_SPEED_BOTTOM']} = Status indicator (always on)")
    print(f"  - LED #{config['WIND_SPEED_TOP']} = Wind direction (colored by direction)")
    print()

    for wind_knots in [10, 20, 30]:
        num_leds, lit_leds, wind_mps = calculate_wind_speed_leds(wind_knots, config)

        if num_leds == 0:
            print(f"  {wind_knots} knots ({wind_mps:.1f} m/s) → No data LEDs (below minimum)")
        elif num_leds >= (config['WIND_SPEED_LENGTH'] - 2):
            print(f"  {wind_knots} knots ({wind_mps:.1f} m/s) → ALL {num_leds} data LEDs (maximum)")
        else:
            # Find the topmost lit LED (the marker position)
            marker_led = lit_leds[-1] if lit_leds else None
            print(f"  {wind_knots} knots ({wind_mps:.1f} m/s) → {num_leds} data LEDs lit → Mark at LED #{marker_led}")

        # Show all lit LED indices for reference
        if lit_leds:
            print(f"         Lit data LEDs: {lit_leds}")
        print()


def print_summary(config):
    """Print summary of marker positions."""
    print("=" * 70)
    print("PHYSICAL MARKING GUIDE")
    print("=" * 70)
    print()
    print("Use stickers, tape, or permanent marker to label these LED positions:")
    print()

    # Wave height markers
    print("WAVE HEIGHT STRIP:")
    for height_m in [1.0, 2.0, 3.0]:
        num_leds, lit_leds = calculate_wave_height_leds(height_m, config)
        if lit_leds and num_leds < config['WAVE_HEIGHT_LENGTH']:
            marker_led = lit_leds[-1]
            print(f"  → Mark LED #{marker_led:2d} = {height_m}m waves")
    print()

    # Wind speed markers
    print("WIND SPEED STRIP:")
    for wind_knots in [10, 20, 30]:
        num_leds, lit_leds, _ = calculate_wind_speed_leds(wind_knots, config)
        if lit_leds and num_leds < (config['WIND_SPEED_LENGTH'] - 2):
            marker_led = lit_leds[-1]
            print(f"  → Mark LED #{marker_led:2d} = {wind_knots} knots")
    print()
    print("=" * 70)


def main():
    """Main execution."""
    # Find Config.h in lamp_template directory (one level up)
    config_path = Path(__file__).parent.parent / "lamp_template" / "Config.h"

    if not config_path.exists():
        print(f"❌ Error: Config.h not found at {config_path}")
        print()
        print("Usage: Run this script from the Legends_marking directory")
        print("  cd /path/to/lamp_refractored/Legends_marking")
        print("  python calculate_led_markers.py")
        sys.exit(1)

    # Parse configuration
    config = parse_config_h(config_path)

    # Print results
    print_header(config)
    print_wave_height_markers(config)
    print_wind_speed_markers(config)
    print_summary(config)

    print()
    print("✅ Calculation complete!")
    print()


if __name__ == "__main__":
    main()
