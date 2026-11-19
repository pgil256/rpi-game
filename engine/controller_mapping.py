"""Calibrate digital D-pads that report hats, arbitrary axes, or buttons."""

import math

DIRECTIONS = {"up": (0, -1), "right": (1, 0), "down": (0, 1), "left": (-1, 0)}


BUTTON_NAMES = ("a", "b", "select", "start")


def controller_profile(config, guid):
    """Read both historical flat profiles and previously calibrated devices."""
    if not guid or config.get("controller_guid") in (None, guid):
        return {k: v for k, v in config.items() if k != "other_profiles"}
    others = config.get("other_profiles", {})
    profile = others.get(guid) if isinstance(others, dict) else None
    return dict(profile) if isinstance(profile, dict) else {}


def save_profile(store, guid, name, changes):
    config = store.load()
    previous = config.get("controller_guid")
    others = config.get("other_profiles", {})
    others = dict(others) if isinstance(others, dict) else {}
    if isinstance(previous, str) and previous != guid:
        others[previous] = controller_profile(config, previous)
    profile = controller_profile(config, guid)
    if "buttons" in changes:
        buttons = profile.get("buttons", {})
        buttons = dict(buttons) if isinstance(buttons, dict) else {}
        changes = dict(changes, buttons={**buttons, **changes["buttons"]})
    profile.update(changes, controller_guid=guid, controller_name=name)
    others.pop(guid, None)
    if others:
        profile["other_profiles"] = others
    return store.save(profile)


def button_conflict(name, button, current, assigning, captured, reserved):
    if button in reserved:
        return "That button controls the D-pad."
    if button in captured.values():
        return "That button was already captured."
    if any(
        key != name and key not in assigning and value == button for key, value in current.items()
    ):
        return "Already assigned. Choose all four buttons to swap them."
    return ""


def valid_binding(binding):
    if not isinstance(binding, dict):
        return False
    index = binding.get("index")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return False
    kind = binding.get("kind")
    if kind == "button":
        return True
    value = binding.get("value")
    if kind == "hat":
        return isinstance(value, (list, tuple)) and tuple(value) in DIRECTIONS.values()
    if kind == "axis":
        center = binding.get("center", 0)
        return (
            all(
                isinstance(v, (int, float))
                and not isinstance(v, bool)
                and math.isfinite(v)
                and -1.01 <= v <= 1.01
                for v in (value, center)
            )
            and abs(value - center) >= 0.5
        )
    return False


def valid_bindings(bindings):
    if not isinstance(bindings, dict) or set(bindings) != set(DIRECTIONS):
        return False
    if not all(valid_binding(binding) for binding in bindings.values()):
        return False
    # The same physical signal cannot mean two different cardinal directions.
    identities = {(b["kind"], b["index"], str(b.get("value"))) for b in bindings.values()}
    return len(identities) == 4


def detect_binding(neutral, pressed):
    for index, value in enumerate(pressed["hats"]):
        if tuple(value) in DIRECTIONS.values():
            return {"kind": "hat", "index": index, "value": list(value)}
    changes = [
        (abs(value - neutral["axes"][i]), i, value)
        for i, value in enumerate(pressed["axes"])
        if i < len(neutral["axes"])
    ]
    if changes:
        distance, index, value = max(changes)
        if distance >= 0.5:
            return {
                "kind": "axis",
                "index": index,
                "value": round(value, 4),
                "center": round(neutral["axes"][index], 4),
            }
    for index, value in enumerate(pressed["buttons"]):
        if value and (index >= len(neutral["buttons"]) or not neutral["buttons"][index]):
            return {"kind": "button", "index": index}
    return None


def is_neutral(neutral, current):
    return (
        len(neutral["axes"]) == len(current["axes"])
        and all(abs(a - b) < 0.15 for a, b in zip(neutral["axes"], current["axes"]))
        and all(tuple(hat) == (0, 0) for hat in current["hats"])
        and not any(current["buttons"])
    )


def binding_pressed(binding, axes, hats, buttons):
    index = binding["index"]
    if binding["kind"] == "button":
        return bool(buttons.get(index, False))
    if binding["kind"] == "hat":
        hx, hy = hats.get(index, (0, 0))
        bx, by = binding["value"]
        return bool((bx and hx == bx) or (by and hy == by))
    # Exact digital positions also support D-pads encoded on a single axis.
    # Unbound axes and their idle noise never contribute to movement.
    value = axes.get(index, binding.get("center", 0))
    tolerance = min(0.2, abs(binding["value"] - binding.get("center", 0)) / 3)
    return abs(value - binding["value"]) <= tolerance


def decode_bindings(bindings, axes, hats, buttons):
    held = {
        name: binding_pressed(binding, axes, hats, buttons) for name, binding in bindings.items()
    }
    return (int(held["right"]) - int(held["left"]), int(held["down"]) - int(held["up"]))
