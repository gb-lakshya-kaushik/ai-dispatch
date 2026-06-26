"""Shared rule definitions and constants for the dispatch engines."""



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



def driver_class_meets_requirement(has_class: str | None, required_class: str) -> bool:
    """Check if a driver's class meets or exceeds the required class."""
    if has_class is None:
        return False
    # Handle simple classes
    req_base = required_class
    if req_base not in DRIVER_CLASS_HIERARCHY:
        # e.g. "D1+ & LT", we only check the base class here and let the caller check certs
        if "+" in req_base:
            req_base = req_base.split("+")[0]
        if req_base not in DRIVER_CLASS_HIERARCHY:
            return False

    try:
        has_idx = DRIVER_CLASS_HIERARCHY.index(has_class)
        req_idx = DRIVER_CLASS_HIERARCHY.index(req_base)
        return has_idx >= req_idx
    except ValueError:
        return False

def vehicle_driver_meets_requirement(
    driver_class: str | None,
    certifications: list[str],
    vehicle_type: str,
    required_driver_class: str,
    operating_state: str,
    is_freeway: bool,
) -> bool:
    if not driver_class_meets_requirement(driver_class, required_driver_class):
        # Contingency: If TMA is needed on non-freeway job, D3 or D4 can be used
        if "TMA" in vehicle_type and not is_freeway:
            if driver_class in ("D3", "D4"):
                return True
        return False

    if "LT" in required_driver_class or "Light Tower" in vehicle_type:
        if "Light Tower Certification" not in certifications:
            return False
            
    if "AFAD" in required_driver_class or "AFAD" in vehicle_type:
        if "AFAD Certification" not in certifications:
            return False

    if "Stakebed" in vehicle_type:
        if operating_state not in ("CA", "WA"):
            if "DOT Medical Card" not in certifications:
                return False
        if operating_state == "MI":
            if "Chauffeur License" not in certifications:
                return False

    return True
