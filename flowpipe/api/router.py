"""
FlowPipe FastAPI Router

Provides REST API endpoints for workflow management and execution:
  GET  /api/v1/workflow/nodes          - List all registered nodes
  GET  /api/v1/workflow/nodes/:name    - Get single node schema
  GET  /api/v1/workflow/               - List saved workflows
  GET  /api/v1/workflow/default        - Get default workflow
  POST /api/v1/workflow                - Save a workflow
  GET  /api/v1/workflow/:id            - Get a saved workflow
  PUT  /api/v1/workflow/:id            - Update a workflow
  DELETE /api/v1/workflow/:id          - Delete a workflow
  POST /api/v1/workflow/validate       - Validate a workflow
  POST /api/v1/workflow/execute        - Execute a workflow (async via Celery)
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.api.deps import get_current_user
from app.utils.logger import logger
from app.utils.response import success_response, list_response, message_response

from flowpipe.core.registry import NodeRegistry
from flowpipe.core.schema import dict_to_workflow
from flowpipe.core.validator import Validator
from flowpipe.schemas.workflow_schema import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    WorkflowExecuteRequest,
    NodeSchemaResponse,
    NodeListResponse,
)

# Import nodes to ensure they're registered
import flowpipe.nodes  # noqa: F401


router = APIRouter(prefix="/api/v1/workflow", tags=["Workflow"])


# ------------------------------------------------------------------
# Node discovery endpoints
# ------------------------------------------------------------------

@router.get("/nodes")
async def list_nodes(
    current_user: dict = Depends(get_current_user),
):
    """List all registered workflow nodes with their schemas."""
    nodes = NodeRegistry.list_all()
    categories = NodeRegistry.get_by_category()
    return success_response(data={
        "nodes": nodes,
        "categories": categories,
    })


@router.get("/nodes/{name}")
async def get_node_schema(
    name: str,
    current_user: dict = Depends(get_current_user),
):
    """Get detailed schema for a specific node type."""
    if not NodeRegistry.has(name):
        return message_response(
            message=f"Node type '{name}' not found",
            code=404,
        )
    node_cls = NodeRegistry.get(name)
    return success_response(data=node_cls.get_schema())


# ------------------------------------------------------------------
# Workflow CRUD endpoints
# ------------------------------------------------------------------

@router.get("/")
async def list_workflows(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all saved workflows."""
    from flowpipe.models import WorkflowRecord

    result = await db.execute(
        select(WorkflowRecord).order_by(WorkflowRecord.updated_at.desc())
    )
    workflows = result.scalars().all()

    items = [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "workflow_json": json.loads(w.workflow_json),
            "is_default": bool(w.is_default),
            "created_at": str(w.created_at),
            "updated_at": str(w.updated_at),
        }
        for w in workflows
    ]
    return success_response(data={"items": items, "total": len(items)})


@router.get("/default")
async def get_default_workflow(
    current_user: dict = Depends(get_current_user),
):
    """Get the built-in default three-view generation workflow."""
    from flowpipe.nodes import DEFAULT_THREE_VIEW_WORKFLOW
    return success_response(data=DEFAULT_THREE_VIEW_WORKFLOW)


@router.get("/templates")
async def list_workflow_templates(
    current_user: dict = Depends(get_current_user),
):
    """List all built-in workflow templates."""
    from flowpipe.nodes import BUILTIN_WORKFLOW_TEMPLATES
    return success_response(data=BUILTIN_WORKFLOW_TEMPLATES)


@router.post("")
async def create_workflow(
    request: WorkflowCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Save a new workflow."""
    from flowpipe.models import WorkflowRecord

    record = WorkflowRecord(
        name=request.name,
        description=request.description,
        workflow_json=json.dumps(request.workflow_json, ensure_ascii=False),
        is_default=request.is_default,
        created_by=current_user.get("id"),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return success_response(data={
        "id": record.id,
        "name": record.name,
        "message": "Workflow saved",
    })


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a saved workflow by ID."""
    from flowpipe.models import WorkflowRecord

    result = await db.execute(
        select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return message_response(message=f"Workflow {workflow_id} not found", code=404)

    return success_response(data={
        "id": record.id,
        "name": record.name,
        "description": record.description,
        "workflow_json": json.loads(record.workflow_json),
        "is_default": bool(record.is_default),
    })


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: int,
    request: WorkflowUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a saved workflow."""
    from flowpipe.models import WorkflowRecord
    from datetime import datetime

    result = await db.execute(
        select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return message_response(message=f"Workflow {workflow_id} not found", code=404)

    if request.name is not None:
        record.name = request.name
    if request.description is not None:
        record.description = request.description
    if request.workflow_json is not None:
        record.workflow_json = json.dumps(request.workflow_json, ensure_ascii=False)
    if request.is_default is not None:
        record.is_default = request.is_default
    record.updated_at = datetime.now()

    await db.commit()
    return success_response(data={"id": record.id, "message": "Workflow updated"})


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a saved workflow."""
    from flowpipe.models import WorkflowRecord

    result = await db.execute(
        delete(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    await db.commit()

    if result.rowcount == 0:
        return message_response(message=f"Workflow {workflow_id} not found", code=404)

    return message_response(message="Workflow deleted")


# ------------------------------------------------------------------
# Validation & Execution endpoints
# ------------------------------------------------------------------

@router.post("/validate")
async def validate_workflow(
    request: WorkflowValidateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Validate a workflow without executing it."""
    workflow = dict_to_workflow(request.workflow_json)
    errors = Validator.validate(workflow, NodeRegistry)
    return success_response(data={
        "valid": len(errors) == 0,
        "errors": errors,
    })


@router.post("/execute")
async def execute_workflow(
    request: WorkflowExecuteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Execute a workflow asynchronously via Celery.

    Either provide workflow_id (to use a saved workflow) or
    workflow_json (inline workflow definition).
    """
    # Resolve workflow JSON
    workflow_json = request.workflow_json
    if workflow_json is None and request.workflow_id:
        from flowpipe.models import WorkflowRecord
        result = await db.execute(
            select(WorkflowRecord).where(WorkflowRecord.id == request.workflow_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return message_response(
                message=f"Workflow {request.workflow_id} not found", code=404
            )
        workflow_json = json.loads(record.workflow_json)

    if workflow_json is None:
        return message_response(
            message="Provide either workflow_id or workflow_json", code=400
        )

    # Validate first
    workflow = dict_to_workflow(workflow_json)
    errors = Validator.validate(workflow, NodeRegistry)
    if errors:
        return success_response(data={"valid": False, "errors": errors})

    # Inject business context into runtime_inputs
    runtime_inputs = dict(request.runtime_inputs or {})
    if request.ip_asset_id is not None:
        runtime_inputs["ip_asset_id"] = request.ip_asset_id
    if request.view_type is not None:
        runtime_inputs["view_type"] = request.view_type

    # Submit to Celery
    from celery_worker import execute_workflow_task
    task = execute_workflow_task.delay(
        workflow_json=workflow_json,
        runtime_inputs=runtime_inputs,
    )

    # Create TaskRecord so the task is visible in Task Monitor
    try:
        from app.models.task import TaskRecord
        task_record = TaskRecord(
            task_id=task.id,
            task_type="workflow_execution",
            ip_asset_id=request.ip_asset_id,
            status="pending",
            parameters={
                "workflow_name": workflow.name,
                "runtime_inputs": {k: str(v)[:200] for k, v in runtime_inputs.items()},
            },
            created_by=current_user.get("id", 1),
            created_at=datetime.now(),
        )
        db.add(task_record)
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to create TaskRecord for workflow task: {e}")

    logger.info(f"Workflow submitted: task_id={task.id}, workflow='{workflow.name}'")

    return success_response(data={
        "task_id": task.id,
        "status": "submitted",
        "workflow_name": workflow.name,
    })
