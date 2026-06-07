"""
FlowPipe Node Registry

Central registry for all node classes. Nodes register themselves
via the ``@register_node`` decorator or ``NodeRegistry.register()``.
"""
from typing import Dict, List, Optional, Type
from collections import defaultdict

from flowpipe.core.node import BaseNode


class NodeNotFoundError(Exception):
    """Raised when a requested node type is not registered."""
    pass


class DuplicateNodeError(Exception):
    """Raised when registering a node with a name that already exists."""
    pass


class NodeRegistry:
    """
    Global registry for workflow node classes.

    Usage::

        @register_node
        class MyNode(BaseNode):
            NAME = "MyNode"
            ...

        # Retrieve
        node_cls = NodeRegistry.get("MyNode")
    """

    _nodes: Dict[str, Type[BaseNode]] = {}

    @classmethod
    def register(cls, node_class: Type[BaseNode]) -> None:
        """Register a node class. Raises DuplicateNodeError on conflict."""
        if not node_class.NAME:
            raise ValueError(f"Node class {node_class.__name__} has empty NAME")
        if node_class.NAME in cls._nodes:
            existing = cls._nodes[node_class.NAME]
            if existing is not node_class:
                raise DuplicateNodeError(
                    f"Node '{node_class.NAME}' already registered by "
                    f"{existing.__name__}, cannot register {node_class.__name__}"
                )
            return  # Already registered (same class)
        cls._nodes[node_class.NAME] = node_class

    @classmethod
    def get(cls, name: str) -> Type[BaseNode]:
        """Get a node class by name. Raises NodeNotFoundError if missing."""
        node_cls = cls._nodes.get(name)
        if node_cls is None:
            available = ", ".join(sorted(cls._nodes.keys())) or "(none)"
            raise NodeNotFoundError(
                f"Node type '{name}' not found. Available: {available}"
            )
        return node_cls

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a node type is registered."""
        return name in cls._nodes

    @classmethod
    def list_all(cls) -> List[dict]:
        """Export schema for all registered nodes (for frontend node panel)."""
        return [node_cls.get_schema() for node_cls in cls._nodes.values()]

    @classmethod
    def get_by_category(cls) -> Dict[str, List[dict]]:
        """
        Organize nodes by category for the frontend node panel.

        Returns::

            {
                "Model/Loader": [{"name": "SDModelLoader", ...}],
                "Preproc/Detect": [{"name": "FaceDetectNode", ...}],
            }
        """
        result = defaultdict(list)
        for node_cls in cls._nodes.values():
            result[node_cls.CATEGORY or "Uncategorized"].append(
                node_cls.get_schema()
            )
        return dict(result)

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove a node from the registry (useful for testing)."""
        cls._nodes.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered nodes (useful for testing)."""
        cls._nodes.clear()


def register_node(cls: Type[BaseNode]) -> Type[BaseNode]:
    """
    Decorator to auto-register a node class.

    Usage::

        @register_node
        class MyNode(BaseNode):
            NAME = "MyNode"
            ...
    """
    NodeRegistry.register(cls)
    return cls
