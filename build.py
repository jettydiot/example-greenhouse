#!/usr/bin/env python3
"""
build.py — generate main/driver_registry.c from device.yaml

No external dependencies required (pure stdlib YAML subset parser).
PyYAML is used automatically if available (e.g. in ESP-IDF Python env).

Usage (called automatically by CMake, or manually):
    python3 build.py device.yaml main/driver_registry.c
"""

import sys
import re

# ── YAML loading ─────────────────────────────────────────────────────────────

def load_yaml(path):
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        return _parse_yaml_simple(path)


def _strip_comment(s):
    """Remove trailing YAML comment (# ...) but not inside quoted strings."""
    in_quote = None
    for i, ch in enumerate(s):
        if ch in ('"', "'"):
            if in_quote is None:
                in_quote = ch
            elif in_quote == ch:
                in_quote = None
        elif ch == '#' and in_quote is None:
            return s[:i].rstrip()
    return s


def _coerce(v):
    v = v.strip()
    # strip surrounding quotes
    if (v.startswith('"') and v.endswith('"')) or \
       (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v.lower() == 'true':  return True
    if v.lower() == 'false': return False
    try: return int(v)
    except ValueError: pass
    try: return float(v)
    except ValueError: pass
    return v


def _parse_yaml_simple(path):
    """
    Minimal YAML parser for device.yaml.
    Handles:
      - nested key: value mappings
      - lists of scalars and dicts with indented sub-keys
    Uses an index-based recursive approach rather than a fragile stack machine.
    """
    raw_lines = open(path).readlines()

    # Pre-process: strip blank lines and comments, record (indent, text)
    lines = []
    for raw in raw_lines:
        line = raw.rstrip()
        if not line:
            continue
        stripped = line.lstrip()
        if stripped.startswith('#'):
            continue
        lines.append((len(line) - len(stripped), stripped))

    def parse_value(i, base_indent):
        """
        Parse one value starting at lines[i], where the value's content is
        indented > base_indent.  Returns (value, next_i).
        The value is a dict, list, or scalar.
        """
        if i >= len(lines):
            return {}, i

        child_indent = lines[i][0]
        if child_indent <= base_indent:
            return {}, i

        # Determine if this block is a mapping or sequence
        if lines[i][1].startswith('- '):
            return parse_list(i, base_indent)
        else:
            return parse_dict(i, base_indent)

    def parse_dict(i, base_indent):
        result = {}
        while i < len(lines):
            indent, text = lines[i]
            if indent <= base_indent:
                break
            if text.startswith('- '):
                break  # unexpected — stop
            if ':' not in text:
                i += 1
                continue

            k, _, v = text.partition(':')
            k = k.strip()
            v = _strip_comment(v).strip()

            if v == '':
                # Value is on the following indented lines
                i += 1
                child, i = parse_value(i, indent)
                result[k] = child
            else:
                result[k] = _coerce(v)
                i += 1
        return result, i

    def parse_list(i, base_indent):
        result = []
        while i < len(lines):
            indent, text = lines[i]
            if indent <= base_indent:
                break
            if not text.startswith('- '):
                break

            content = _strip_comment(text[2:]).strip()
            i += 1

            if ':' in content:
                # Dict item — first k:v on this line, more may follow at indent+2
                item = {}
                k, _, v = content.partition(':')
                k = k.strip()
                v = _strip_comment(v).strip()
                item[k] = _coerce(v) if v else None

                # Consume indented sub-keys
                sub, i = parse_dict(i, indent)
                item.update(sub)

                # Fix None placeholder (key with value on next indented lines)
                for sk in list(item.keys()):
                    if item[sk] is None:
                        # look ahead already consumed by parse_dict
                        item[sk] = {}
                result.append(item)
            else:
                result.append(_coerce(content))
        return result, i

    result, _ = parse_dict(0, -1)
    return result


# ── Driver metadata ───────────────────────────────────────────────────────────

DRIVERS = {
    "dht22":        ("dht22.h",         "dht22_config_t",         "dht22_register"),
    "ds18b20":      ("ds18b20.h",       "ds18b20_config_t",       "ds18b20_register"),
    "bme280":       ("bme280.h",        "bme280_config_t",        "bme280_register"),
    "relay":        ("relay.h",         "relay_config_t",         "relay_register"),
    "led":          ("led.h",           "led_config_t",           "led_register"),
    "button":       ("button.h",        "button_config_t",        "button_register"),
    "soil_moisture":("soil_moisture.h", "soil_moisture_config_t", "soil_moisture_register"),
    "pwm_output":   ("pwm_output.h",    "pwm_output_config_t",    "pwm_output_register"),
    "hcsr04":       ("hcsr04.h",        "hcsr04_config_t",        "hcsr04_register"),
    "ina219":       ("ina219.h",        "ina219_config_t",        "ina219_register"),
}


def c_val(v):
    if isinstance(v, bool):  return "true" if v else "false"
    if isinstance(v, str):   return f'"{v}"'
    return str(v)


# ── Code generator ────────────────────────────────────────────────────────────

def generate(yaml_path, out_path):
    try:
        cfg = load_yaml(yaml_path)
    except Exception as e:
        print(f"[build.py] Failed to parse {yaml_path}: {e}", file=sys.stderr)
        sys.exit(1)

    drivers = cfg.get("drivers", [])
    if not isinstance(drivers, list):
        drivers = []

    headers   = []
    reg_lines = []

    for drv in drivers:
        if not isinstance(drv, dict):
            continue
        name     = str(drv.get("name", "")).lower()
        instance = str(drv.get("instance", name))
        config   = drv.get("config", {})
        if not isinstance(config, dict):
            config = {}

        if name not in DRIVERS:
            print(f"[build.py] Unknown driver '{name}' — skipping", file=sys.stderr)
            continue

        header, struct, fn = DRIVERS[name]
        if header not in headers:
            headers.append(header)

        safe   = re.sub(r'\W', '_', instance)
        fields = ", ".join(f".{k} = {c_val(v)}" for k, v in config.items())
        reg_lines.append(f'    {struct} {safe}_cfg = {{ {fields} }};')
        reg_lines.append(f'    {fn}("{instance}", &{safe}_cfg);')
        reg_lines.append("")

    out = [
        "/**",
        " * driver_registry.c — AUTO-GENERATED from device.yaml",
        " * Do not edit manually. Edit device.yaml and rebuild.",
        " */",
        "",
        '#include "jettyd_driver.h"',
    ]
    for h in headers:
        out.append(f'#include "{h}"')
    out += ["", "void jettyd_register_drivers(void)", "{"]
    if reg_lines:
        out += reg_lines
    else:
        out.append("    /* No drivers configured in device.yaml */")
    out += ["}", ""]

    with open(out_path, "w") as f:
        f.write("\n".join(out))

    print(f"[build.py] {len(drivers)} driver(s) → {out_path}")

    # Also emit a CMake fragment listing the driver components that must be
    # added to main's REQUIRES so their include dirs are on the include path.
    cmake_path = out_path.replace("driver_registry.c", "driver_requires.cmake")
    active_components = [d.get("name", "") for d in drivers if isinstance(d, dict)
                         and d.get("name", "").lower() in DRIVERS]
    cmake_lines = [
        "# AUTO-GENERATED by build.py — do not edit manually",
        "# List of ESP-IDF component names for active drivers in device.yaml",
        "set(JETTYD_DRIVER_REQUIRES",
    ]
    for comp in active_components:
        cmake_lines.append(f"    {comp}")
    cmake_lines.append(")")
    with open(cmake_path, "w") as f:
        f.write("\n".join(cmake_lines) + "\n")
    print(f"[build.py] driver REQUIRES → {cmake_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <device.yaml> <output.c>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2])
