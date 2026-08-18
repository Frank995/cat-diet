import json

from nutrients import *


def keys_view(d):
    """Return a nested dict with the same keys, all leaf values replaced by None."""
    return {k: keys_view(v) if isinstance(v, dict) else None for k, v in d.items()}


def merge_views(a, b):
    """
    Recursively merge two key‑views.
    - If one side is None and the other is a dict, keep the dict.
    - If both are dicts, merge their keys recursively.
    - If both are None, return None.
    """
    if a is None:
        return b
    if b is None:
        return a

    # Both are dicts – merge all keys from both
    merged = {}
    all_keys = set(a.keys()) | set(b.keys())
    for k in all_keys:
        if k in a and k in b:
            merged[k] = merge_views(a[k], b[k])
        elif k in a:
            merged[k] = a[k]
        else:
            merged[k] = b[k]
    return merged


if __name__ == "__main__":
    output = {}
    for name, value in list(locals().items()):
        if name.endswith("_TABLE"):
            view = keys_view(value)
            output = merge_views(output, view)
    print(json.dumps(output, indent=4))
