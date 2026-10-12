#!/usr/bin/env python3
"""Compare two config files as FLAT key/value pairs.

Purpose: assess how much REAL damage a config rewrite did, ignoring
formatting noise (re-indentation, comment stripping, key reordering).

Usage:
    python3 config_damage_diff.py <reference_file> <suspect_file>

Typical use: a third-party installer re-serialized your config and stripped
all comments. Run this BEFORE deciding to roll back: if the only functional
differences are the ones you expected, restoring the backup loses nothing.

Exit codes:
    0 = no functional differences (formatting-only change)
    1 = functional differences found
    2 = could not load one of the files
"""

import json
import os
import sys


def load(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if ext == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError:
        sys.exit("need pyyaml: pip install pyyaml")
    return yaml.safe_load(text)


def flatten(node, prefix=""):
    """Recursively flatten a nested structure into {"dotted.path": leaf}."""
    out = {}
    if isinstance(node, dict):
        for key, val in node.items():
            out.update(flatten(val, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for idx, val in enumerate(node):
            out.update(flatten(val, f"{prefix}[{idx}]"))
    else:
        out[prefix] = node
    return out


def main(argv):
    if len(argv) != 3:
        sys.exit("usage: config_damage_diff.py <reference_file> <suspect_file>")
    ref_path, sus_path = argv[1], argv[2]

    try:
        ref_raw, sus_raw = load(ref_path), load(sus_path)
    except Exception as exc:  # noqa: BLE001 - report and exit, do not traceback
        print(f"FAILED to load: {exc}")
        return 2

    ref, sus = flatten(ref_raw), flatten(sus_raw)
    only_ref = sorted(set(ref) - set(sus))
    only_sus = sorted(set(sus) - set(ref))
    changed = [(k, ref[k], sus[k]) for k in sorted(set(ref) & set(sus)) if ref[k] != sus[k]]

    print(f"reference: {ref_path}")
    print(f"suspect  : {sus_path}")
    print()

    print(f"only in reference ({len(only_ref)}):")
    for key in only_ref:
        print(f"    {key} = {ref[key]!r}")

    print(f"only in suspect ({len(only_sus)}):")
    for key in only_sus:
        print(f"    {key} = {sus[key]!r}")

    print(f"values differ ({len(changed)}):")
    for key, lhs, rhs in changed:
        print(f"    {key}")
        print(f"        reference: {lhs!r}")
        print(f"        suspect  : {rhs!r}")

    # A config that points into a scratch/temp dir loads and parses fine but
    # can never work -- the referenced binary or path will be gone.
    broken = [
        (key, val)
        for key, val in sus.items()
        if isinstance(val, str) and val.startswith(("/tmp/", "/var/tmp/"))
    ]
    if broken:
        print(f"paths pointing into a temp dir ({len(broken)}) -- these will not work:")
        for key, val in broken:
            print(f"    {key} = {val!r}")

    total = len(only_ref) + len(only_sus) + len(changed)
    print()
    print(f"FUNCTIONAL DIFFERENCES: {total}")
    if total == 0:
        print("-> formatting-only change; comments may still have been lost.")
    else:
        print("-> check each item above is an intended change before rolling back.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
