"""
FlowPipe API Schemas

Pydantic models for workflow API request/response validation.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Node schemas ---

class NodePosition(BaseModel):
    x: float = 0
    y: float = 0


class NodeInstanceSchema(BaseModel):
    id: str = Field(..., description="Unique node instance ID")
    type: str = Field(..., description="Node type name (must be registered)")
    position: NodePosition = Field(default_factory=NodePosition)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class EdgeSchema(BaseModel):
    source: str = Field(..., description="Source node ID")
    source_output: str = Field(default="", description="Source output port name")
    target: str = Field(..., description="Target node ID")
    target_input: str = Field(default="", description="Target input port name")


# --- Workflow schemas ---

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    workflow_json: Dict[str, Any] = Field(..., description="Complete workflow JSON")
    is_default: bool = False


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    workflow_json: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    workflow_json: Dict[str, Any]
    is_default: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowListResponse(BaseModel):
    items: List[WorkflowResponse]
    total: int


# --- Execution schemas ---

class WorkflowValidateRequest(BaseModel):
    workflow_json: Dict[str, Any] = Field(..., description="Workflow to validate")


class WorkflowValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)


class WorkflowExecuteRequest(BaseModel):
    workflow_id: Optional[int] = Field(default=None, description="Saved workflow ID (or use workflow_json)")
    workflow_json: Optional[Dict[str, Any]] = Field(default=None, description="Inline workflow JSON")
    runtime_inputs: Dict[str, Any] = Field(default_factory=dict, description="Runtime inputs (e.g. image paths)")


class NodeSchemaResponse(BaseModel):
    name: str
    display_name: str
    category: str
    description: str
    input_types: Dict[str, Any]
    return_types: Dict[str, str]
    output_node: bool


class NodeListResponse(BaseModel):
    nodes: List[NodeSchemaResponse]
    categories: Dict[str, List[NodeSchemaResponse]]
