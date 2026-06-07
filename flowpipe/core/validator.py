"""
FlowPipe Workflow Validator

Validates workflow DAGs before execution:
- Cycle detection (Kahn's algorithm)
- Port type compatibility
- Required input satisfaction
- Parameter legality
"""
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque

from flowpipe.core.workflow import Workflow, NodeInstance, Edge
from flowpipe.core.registry import NodeRegistry
from flowpipe.core.types import is_port_compatible


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(
            f"Workflow validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


class Validator:
    """Validates a Workflow against the NodeRegistry."""

    @staticmethod
    def validate(workflow: Workflow, registry: NodeRegistry = None) -> List[str]:
        """
        Run all validation checks. Returns a list of error messages.
        Empty list means the workflow is valid.
        """
        errors: List[str] = []

        # Basic structural checks
        errors.extend(Validator._check_unique_ids(workflow))
        errors.extend(Validator._check_node_types_exist(workflow, registry))

        if errors:
            return errors  # Skip further checks if basic structure is broken

        # DAG checks
        errors.extend(Validator._check_edge_references(workflow))
        errors.extend(Validator._check_dag_acyclic(workflow))

        # Port and parameter checks
        errors.extend(Validator._check_port_types(workflow, registry))
        errors.extend(Validator._check_required_inputs(workflow, registry))

        return errors

    @staticmethod
    def validate_or_raise(workflow: Workflow, registry: NodeRegistry = None):
        """Validate and raise WorkflowValidationError if invalid."""
        errors = Validator.validate(workflow, registry)
        if errors:
            raise WorkflowValidationError(errors)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_unique_ids(workflow: Workflow) -> List[str]:
        """Ensure all node IDs are unique."""
        errors = []
        seen: Set[str] = set()
        for node in workflow.nodes:
            if node.id in seen:
                errors.append(f"Duplicate node ID: '{node.id}'")
            seen.add(node.id)
        return errors

    @staticmethod
    def _check_node_types_exist(workflow: Workflow, registry: NodeRegistry) -> List[str]:
        """Ensure all node types are registered."""
        if registry is None:
            return []
        errors = []
        for node in workflow.nodes:
            if not registry.has(node.type):
                errors.append(
                    f"Node '{node.id}': unknown type '{node.type}'"
                )
        return errors

    # Virtual node ID used for runtime input injection
    RUNTIME_NODE_ID = "__runtime__"

    @staticmethod
    def _check_edge_references(workflow: Workflow) -> List[str]:
        """Ensure edges reference existing node IDs (or __runtime__)."""
        errors = []
        node_ids = set(workflow.get_node_ids())

        for i, edge in enumerate(workflow.edges):
            if edge.source_id != Validator.RUNTIME_NODE_ID and edge.source_id not in node_ids:
                errors.append(
                    f"Edge {i}: source node '{edge.source_id}' does not exist"
                )
            if edge.target_id not in node_ids:
                errors.append(
                    f"Edge {i}: target node '{edge.target_id}' does not exist"
                )
        return errors

    @staticmethod
    def _check_dag_acyclic(workflow: Workflow) -> List[str]:
        """
        Detect cycles using Kahn's algorithm (topological sort).
        Returns error if a cycle is found.
        """
        if not workflow.nodes:
            return []

        # Build adjacency list and in-degree count
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = defaultdict(int)

        node_ids = set(workflow.get_node_ids())
        for nid in node_ids:
            in_degree[nid] = 0

        # Include __runtime__ as a virtual source node
        has_runtime_edges = any(
            e.source_id == Validator.RUNTIME_NODE_ID for e in workflow.edges
        )
        if has_runtime_edges:
            in_degree[Validator.RUNTIME_NODE_ID] = 0

        for edge in workflow.edges:
            adj[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] += 1

        # Start with nodes that have no incoming edges
        queue = deque(nid for nid in in_degree if in_degree[nid] == 0)
        visited_count = 0

        while queue:
            nid = queue.popleft()
            visited_count += 1
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        expected = len(node_ids) + (1 if has_runtime_edges else 0)
        if visited_count < expected:
            return ["Workflow contains a cycle (not a valid DAG)"]
        return []

    @staticmethod
    def _check_port_types(workflow: Workflow, registry: NodeRegistry) -> List[str]:
        """Check that connected port types are compatible."""
        if registry is None:
            return []

        errors = []
        for i, edge in enumerate(workflow.edges):
            # Skip type checking for __runtime__ edges (no registered node)
            if edge.source_id == Validator.RUNTIME_NODE_ID:
                # Validate target port exists
                target_node = workflow.get_node(edge.target_id)
                if not target_node:
                    continue
                try:
                    target_cls = registry.get(target_node.type)
                except Exception:
                    continue
                if target_cls.get_input_type(edge.target_input) is None:
                    errors.append(
                        f"Edge {i}: target node '{edge.target_id}' has no "
                        f"input port '{edge.target_input}'"
                    )
                continue

            source_node = workflow.get_node(edge.source_id)
            target_node = workflow.get_node(edge.target_id)
            if not source_node or not target_node:
                continue

            try:
                source_cls = registry.get(source_node.type)
                target_cls = registry.get(target_node.type)
            except Exception:
                continue  # Already caught by _check_node_types_exist

            source_type = source_cls.get_output_type(edge.source_output)
            target_type = target_cls.get_input_type(edge.target_input)

            if source_type is None:
                errors.append(
                    f"Edge {i}: source node '{edge.source_id}' has no "
                    f"output port '{edge.source_output}'"
                )
                continue

            if target_type is None:
                errors.append(
                    f"Edge {i}: target node '{edge.target_id}' has no "
                    f"input port '{edge.target_input}'"
                )
                continue

            if not is_port_compatible(source_type, target_type):
                errors.append(
                    f"Edge {i}: type mismatch - "
                    f"'{edge.source_id}.{edge.source_output}' ({source_type}) -> "
                    f"'{edge.target_id}.{edge.target_input}' ({target_type})"
                )

        return errors

    @staticmethod
    def _check_required_inputs(workflow: Workflow, registry: NodeRegistry) -> List[str]:
        """Check that all required inputs are satisfied (by edge or parameter)."""
        if registry is None:
            return []

        errors = []
        for node in workflow.nodes:
            try:
                node_cls = registry.get(node.type)
            except Exception:
                continue

            input_defs = node_cls.INPUT_TYPES()
            required = input_defs.get("required", {})

            # Ports satisfied by edges
            connected_inputs: Set[str] = set()
            for edge in workflow.get_incoming_edges(node.id):
                connected_inputs.add(edge.target_input)

            for param_name, entry in required.items():
                # Skip if connected via edge
                if param_name in connected_inputs:
                    continue

                # Skip if marked as runtime-injected (provided at execution time)
                if isinstance(entry, tuple) and len(entry) >= 2:
                    config = entry[1]
                    if isinstance(config, dict) and config.get("runtime"):
                        continue

                # Check if parameter value is provided
                if param_name in node.parameters:
                    continue

                # Check if it has a default
                if isinstance(entry, tuple) and len(entry) >= 2:
                    config = entry[1]
                    if isinstance(config, dict) and "default" in config:
                        continue

                # Check if it's a pure type port (expected to be connected)
                type_str = entry[0] if isinstance(entry, tuple) else entry
                # Known port types that should come from edges
                port_types = {
                    "MODEL", "IMAGE", "IMAGE_LIST", "EMBEDDINGS",
                    "FACES", "BBOX",
                }
                if type_str in port_types:
                    errors.append(
                        f"Node '{node.id}' ({node.type}): required input "
                        f"'{param_name}' ({type_str}) is not connected"
                    )

        return errors
