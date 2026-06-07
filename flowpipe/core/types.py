"""
FlowPipe Port Type System

Defines typed ports for node connections. Each port has a type string
that ensures only compatible data flows between nodes.
"""


class PortType:
    """Port type constants for node connections."""

    MODEL = "MODEL"               # diffusers pipeline (StableDiffusionPipeline etc.)
    IMAGE = "IMAGE"               # PIL.Image.Image (single image)
    IMAGE_LIST = "IMAGE_LIST"     # List[PIL.Image.Image] (multiple images)
    EMBEDDINGS = "EMBEDDINGS"     # dict with ip_adapter_image_embeds
    FACES = "FACES"               # insightface detection results (list of Face objects)
    BBOX = "BBOX"                 # face bounding box tuple (x1, y1, x2, y2)
    STRING = "STRING"             # text / string
    INT = "INT"                   # integer
    FLOAT = "FLOAT"               # float
    ANY = "ANY"                   # wildcard (not recommended, bypasses type check)


# Type compatibility matrix: source_type -> set of compatible target types
_TYPE_COMPAT = {
    PortType.ANY: {PortType.ANY},  # ANY connects to ANY only
}

# Scalar types that can auto-widen
_WIDEN_MAP = {
    PortType.INT: {PortType.FLOAT, PortType.STRING},
    PortType.FLOAT: {PortType.STRING},
    PortType.IMAGE: {PortType.IMAGE_LIST},
}


def is_port_compatible(source_type: str, target_type: str) -> bool:
    """
    Check whether a source port type can connect to a target port type.

    Rules:
    - Same type is always compatible
    - ANY on either side is compatible with anything
    - IMAGE -> IMAGE_LIST (auto-wrap)
    - INT -> FLOAT (auto-widen)
    - INT/FLOAT -> STRING (auto-convert)
    """
    if source_type == target_type:
        return True
    if source_type == PortType.ANY or target_type == PortType.ANY:
        return True

    # Check explicit widening rules
    widened = _WIDEN_MAP.get(source_type, set())
    if target_type in widened:
        return True

    return False


# Color mapping for frontend port rendering
PORT_COLORS = {
    PortType.MODEL: "#A855F7",       # purple
    PortType.IMAGE: "#22C55E",       # green
    PortType.IMAGE_LIST: "#16A34A",  # dark green
    PortType.EMBEDDINGS: "#F59E0B",  # amber
    PortType.FACES: "#EF4444",       # red
    PortType.BBOX: "#F97316",        # orange
    PortType.STRING: "#3B82F6",      # blue
    PortType.INT: "#06B6D4",         # cyan
    PortType.FLOAT: "#0891B2",       # dark cyan
    PortType.ANY: "#6B7280",         # gray
}
