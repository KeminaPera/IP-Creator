"""
FlowPipe Node Base Class

Every workflow node is a Python class that inherits from BaseNode.
The pattern is inspired by ComfyUI's node definition style:
  - INPUT_TYPES: classmethod defining input ports and widget parameters
  - RETURN_TYPES: classmethod defining output ports
  - FUNCTION: name of the method to call when executing the node
"""
from typing import Any, Dict, List, Optional


class BaseNode:
    """
    Abstract base class for all workflow nodes.

    Subclasses MUST define:
        NAME          - unique node type identifier (e.g. "SDModelLoader")
        DISPLAY_NAME  - human-readable label (e.g. "SD Model Loader")
        CATEGORY      - menu path for frontend (e.g. "Model/Loader")
        FUNCTION      - name of the execution method

    Subclasses MAY override:
        DESCRIPTION   - tooltip text
        OUTPUT_NODE   - True if this node produces final output (e.g. save)
    """

    NAME: str = ""
    DISPLAY_NAME: str = ""
    CATEGORY: str = ""
    FUNCTION: str = "execute"

    DESCRIPTION: str = ""
    OUTPUT_NODE: bool = False

    # ------------------------------------------------------------------
    # Class methods that subclasses override to declare ports
    # ------------------------------------------------------------------

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        """
        Declare input ports and widget parameters.

        Returns a dict with keys ``required`` and optionally ``optional``.
        Each key maps to a dict of ``{param_name: (type_str, config_dict)}``.

        Example::

            return {
                "required": {
                    "model_id": ("STRING", {
                        "default": "runwayml/stable-diffusion-v1-5",
                        "options": ["runwayml/...", "stabilityai/..."],
                        "label": "Base Model",
                    }),
                    "pipe": ("MODEL", {}),          # connected port
                },
                "optional": {
                    "custom_path": ("STRING", {"default": ""}),
                },
            }

        Config dict keys:
            - default: default value
            - options: list of allowed values (renders as dropdown)
            - label: display label for the widget
            - min / max: numeric range (for INT / FLOAT)
            - step: increment step (for INT / FLOAT)
            - multiline: True for textarea (for STRING)
        """
        return {"required": {}}

    @classmethod
    def RETURN_TYPES(cls) -> Dict[str, str]:
        """
        Declare output ports.

        Returns a dict of ``{port_name: type_str}``.

        Example::

            return {"pipe": "MODEL", "scheduler_name": "STRING"}
        """
        return {}

    # ------------------------------------------------------------------
    # Schema export (used by frontend and API)
    # ------------------------------------------------------------------

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Export full node schema for frontend rendering and API discovery."""
        return {
            "name": cls.NAME,
            "display_name": cls.DISPLAY_NAME,
            "category": cls.CATEGORY,
            "description": cls.DESCRIPTION,
            "input_types": cls.INPUT_TYPES(),
            "return_types": cls.RETURN_TYPES(),
            "output_node": cls.OUTPUT_NODE,
        }

    @classmethod
    def get_input_port_names(cls) -> List[str]:
        """Return all input port names (required + optional)."""
        inputs = cls.INPUT_TYPES()
        names = list(inputs.get("required", {}).keys())
        names.extend(inputs.get("optional", {}).keys())
        return names

    @classmethod
    def get_output_port_names(cls) -> List[str]:
        """Return all output port names."""
        return list(cls.RETURN_TYPES().keys())

    @classmethod
    def get_input_type(cls, port_name: str) -> Optional[str]:
        """Get the type string for a given input port."""
        inputs = cls.INPUT_TYPES()
        for section in ("required", "optional"):
            defs = inputs.get(section, {})
            if port_name in defs:
                entry = defs[port_name]
                # entry is (type_str, config_dict)
                return entry[0] if isinstance(entry, tuple) else entry
        return None

    @classmethod
    def get_output_type(cls, port_name: str) -> Optional[str]:
        """Get the type string for a given output port."""
        return_types = cls.RETURN_TYPES()
        return return_types.get(port_name)

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Extract default values for all parameters (for frontend init)."""
        defaults = {}
        inputs = cls.INPUT_TYPES()
        for section in ("required", "optional"):
            defs = inputs.get(section, {})
            for name, entry in defs.items():
                if isinstance(entry, tuple) and len(entry) >= 2:
                    config = entry[1]
                    if isinstance(config, dict) and "default" in config:
                        defaults[name] = config["default"]
                elif isinstance(entry, str):
                    # Pure type reference with no config
                    defaults[name] = None
        return defaults
