"""Shared rule definitions and constants for the dispatch engines."""

CLOSURE_TYPE_LEAD_SKILL: dict[str, str] = {
    "flagging": "Installer Flagging Operation",
    "single_lane": "Installer Single Lane",
    "multi_lane": "Installer Multi Lane Closure",
    "road_closure": "Installer Road Closure",
    "shoulder_closure": "Installer Shoulder Closure",
    "lane_shift": "Installer Lane Shift",
}

CLOSURE_TYPE_MEMBER_SKILL = "General Assistant"

REQUIRED_CERTIFICATION = "Local Flagger Certification"

# Ordered from lowest to highest capability
DRIVER_CLASS_HIERARCHY = ["DT", "D1", "D2", "D3", "D4"]

# crew_size -> (min_journeymen, max_apprentices)
APPRENTICE_RATIO_RULES: dict[int, tuple[int, int]] = {
    2: (1, 1),
    3: (2, 1),
    4: (3, 1),
    5: (3, 2),
    6: (4, 2),
}

ALL_CLOSURE_TYPES = list(CLOSURE_TYPE_LEAD_SKILL.keys())


def driver_class_meets_requirement(has_class: str | None, required_class: str) -> bool:
    """Check if a driver's class meets or exceeds the required class."""
    if has_class is None:
        return False
    try:
        has_idx = DRIVER_CLASS_HIERARCHY.index(has_class)
        req_idx = DRIVER_CLASS_HIERARCHY.index(required_class)
        return has_idx >= req_idx
    except ValueError:
        return False
