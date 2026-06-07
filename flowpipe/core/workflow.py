"""
FlowPipe Workflow Data Model

Defines the in-memory representation of a workflow: nodes, edges,
and the workflow container itself.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NodeInstance:
    """
    A single node instance within a workflow.

    Attributes:
        id: Unique instance ID within the workflow (e.g. "node_1")
        type: Node class NAME from NodeRegistry (e.g. "SDModelLoader")
        position: Canvas position for frontend rendering
        parameters: User-configured parameter values
    """
    id: str
    type: str
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """
    A directed connection between two node ports.

    Attributes:
        source_id: Source node instance ID
        source_output: Source node output port name
        target_id: Target node instance ID
        target_input: Target node input port name
    """
    source_id: str
    source_output: str
    target_id: str
    target_input: str


@dataclass
class Workflow:
    """
    A complete workflow definition.

    Attributes:
        name: Human-readable workflow name
        version: Schema version for forward compatibility
        nodes: List of node instances
        edges: List of edges connecting nodes
        metadata: Arbitrary metadata (description, tags, etc.)
    """
    name: str
    version: str = "1.0"
    nodes: List[NodeInstance] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[NodeInstance]:
        """Find a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_node_ids(self) -> List[str]:
        """Return all node IDs."""
        return [n.id for n in self.nodes]

    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        """Get all edges pointing TO a node."""
        return [e for e in self.edges if e.target_id == node_id]

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """Get all edges originating FROM a node."""
        return [e for e in self.edges if e.source_id == node_id]
