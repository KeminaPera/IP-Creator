"""
FlowPipe Workflow JSON Schema

Handles serialization (Workflow -> dict) and deserialization (dict -> Workflow)
for storage and API transport.
"""
import json
from typing import Any, Dict

from flowpipe.core.workflow import Workflow, NodeInstance, Edge


def workflow_to_dict(workflow: Workflow) -> Dict[str, Any]:
    """
    Serialize a Workflow to a JSON-compatible dict.

    The output format is designed for:
    - API responses
    - Database storage (as JSON text)
    - Frontend workflow editor state
    """
    return {
        "name": workflow.name,
        "version": workflow.version,
        "nodes": [
            {
                "id": node.id,
                "type": node.type,
                "position": node.position,
                "parameters": node.parameters,
            }
            for node in workflow.nodes
        ],
        "edges": [
            {
                "source": edge.source_id,
                "source_output": edge.source_output,
                "target": edge.target_id,
                "target_input": edge.target_input,
            }
            for edge in workflow.edges
        ],
        "metadata": workflow.metadata,
    }


def dict_to_workflow(data: Dict[str, Any]) -> Workflow:
    """
    Deserialize a dict to a Workflow.

    Accepts both:
    - Full format (from workflow_to_dict)
    - Compact format (from frontend vue-flow)

    The frontend sends edges with "source"/"target" keys matching vue-flow's
    native format.
    """
    nodes = [
        NodeInstance(
            id=n["id"],
            type=n["type"],
            position=n.get("position", {"x": 0, "y": 0}),
            parameters=n.get("parameters", {}),
        )
        for n in data.get("nodes", [])
    ]

    edges = [
        Edge(
            source_id=e["source"],
            source_output=e.get("source_output", e.get("sourceHandle", "")),
            target_id=e["target"],
            target_input=e.get("target_input", e.get("targetHandle", "")),
        )
        for e in data.get("edges", [])
    ]

    return Workflow(
        name=data.get("name", "Untitled Workflow"),
        version=data.get("version", "1.0"),
        nodes=nodes,
        edges=edges,
        metadata=data.get("metadata", {}),
    )


def workflow_to_json(workflow: Workflow, indent: int = 2) -> str:
    """Serialize workflow to JSON string."""
    return json.dumps(workflow_to_dict(workflow), indent=indent, ensure_ascii=False)


def json_to_workflow(json_str: str) -> Workflow:
    """Deserialize workflow from JSON string."""
    return dict_to_workflow(json.loads(json_str))
