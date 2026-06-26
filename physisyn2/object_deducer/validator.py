required_keys = [
    "phenomenon",
    "objects",
    "relations",
    "constraints",
    "topics_to_emphasize",
    "dynamic_explanatory_text",
    "camera_trajectory",
    "scene_graph"
]

def validate(data):
    missing = []

    for key in required_keys:
        if key not in data:
            missing.append(key)

    if missing:
        raise ValueError(
            f"Missing required keys: {missing}"
        )

    return True
