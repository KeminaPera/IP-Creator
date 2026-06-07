"""
FlowPipe -- Lightweight Node-based Workflow Orchestration Engine

A self-contained Python package for building visual, low-code
AI generation pipelines. Inspired by ComfyUI's node architecture.

Quick start::

    from flowpipe import (
        BaseNode, register_node, NodeRegistry,
        Workflow, NodeInstance, Edge,
        WorkflowExecutor, Validator,
        dict_to_workflow, workflow_to_dict,
    )

    @register_node
    class MyNode(BaseNode):
        NAME = "MyNode"
        DISPLAY_NAME = "My Custom Node"
        CATEGORY = "Custom"
        FUNCTION = "run"

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"text": ("STRING", {"default": "hello"})}}

        @classmethod
        def RETURN_TYPES(cls):
            return {"result": "STRING"}

        def run(self, text):
            return {"result": text.upper()}
"""

__version__ = "0.1.0"

# Core types
from flowpipe.core.types import PortType, is_port_compatible, PORT_COLORS

# Node base class
from flowpipe.core.node import BaseNode

# Registry
from flowpipe.core.registry import (
    NodeRegistry,
    register_node,
    NodeNotFoundError,
    DuplicateNodeError,
)

# Workflow data model
from flowpipe.core.workflow import Workflow, NodeInstance, Edge

# JSON serialization
from flowpipe.core.schema import (
    workflow_to_dict,
    dict_to_workflow,
    workflow_to_json,
    json_to_workflow,
)

# Validation
from flowpipe.core.validator import Validator, WorkflowValidationError

# Execution
from flowpipe.core.executor import WorkflowExecutor, ExecutionError

__all__ = [
    # Version
    "__version__",
    # Types
    "PortType",
    "is_port_compatible",
    "PORT_COLORS",
    # Node
    "BaseNode",
    "register_node",
    # Registry
    "NodeRegistry",
    "NodeNotFoundError",
    "DuplicateNodeError",
    # Workflow
    "Workflow",
    "NodeInstance",
    "Edge",
    # Schema
    "workflow_to_dict",
    "dict_to_workflow",
    "workflow_to_json",
    "json_to_workflow",
    # Validator
    "Validator",
    "WorkflowValidationError",
    # Executor
    "WorkflowExecutor",
    "ExecutionError",
]
