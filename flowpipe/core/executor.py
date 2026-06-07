"""
FlowPipe DAG Execution Engine

Executes a validated workflow by:
1. Topological sorting the DAG
2. Executing nodes in dependency order
3. Passing outputs from upstream nodes to downstream inputs
4. Supporting both sync and async node functions
"""
import asyncio
import time
import traceback
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from flowpipe.core.workflow import Workflow, NodeInstance, Edge
from flowpipe.core.registry import NodeRegistry, NodeNotFoundError
from flowpipe.core.validator import Validator, WorkflowValidationError
from flowpipe.core.types import PortType

from app.utils.logger import logger


class ExecutionError(Exception):
    """Raised when a node fails during execution."""

    def __init__(self, node_id: str, node_type: str, original_error: Exception):
        self.node_id = node_id
        self.node_type = node_type
        self.original_error = original_error
        super().__init__(
            f"Node '{node_id}' ({node_type}) failed: {original_error}"
        )


class WorkflowExecutor:
    """
    Executes a FlowPipe workflow.

    Usage::

        executor = WorkflowExecutor()
        result = await executor.execute(workflow, runtime_inputs={
            "ref_image": pil_image,
            "ip_asset_id": 5,
        })
    """

    def __init__(self, registry: Optional[NodeRegistry] = None):
        self.registry = registry or NodeRegistry

    async def execute(
        self,
        workflow: Workflow,
        runtime_inputs: Optional[Dict[str, Any]] = None,
        on_node_start: Optional[Callable] = None,
        on_node_end: Optional[Callable] = None,
        skip_validation: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Execute a workflow and return all node outputs.

        Args:
            workflow: The workflow to execute
            runtime_inputs: External inputs injected as ``__runtime__``
            on_node_start: Callback(node_id, node_type) before each node
            on_node_end: Callback(node_id, node_type, outputs) after each node
            skip_validation: Skip DAG validation (use only for trusted workflows)

        Returns:
            Dict mapping node_id -> {port_name: value}
        """
        # 1. Validate
        if not skip_validation:
            errors = Validator.validate(workflow, self.registry)
            if errors:
                raise WorkflowValidationError(errors)

        # 2. Topological sort
        execution_order = self._topological_sort(workflow)

        # 3. Execute nodes in order
        node_outputs: Dict[str, Dict[str, Any]] = {}

        # Inject runtime inputs as a virtual source node
        if runtime_inputs:
            node_outputs["__runtime__"] = runtime_inputs

        logger.info(
            f"Executing workflow '{workflow.name}': "
            f"{len(execution_order)} nodes, {len(workflow.edges)} edges"
        )

        for node_instance in execution_order:
            node_id = node_instance.id
            node_type = node_instance.type

            if on_node_start:
                on_node_start(node_id, node_type)

            start_time = time.time()

            try:
                # Instantiate node and gather inputs
                node_cls = self.registry.get(node_type)
                node = node_cls()

                inputs = self._gather_inputs(
                    node_instance, workflow, node_outputs, node_cls
                )

                # Execute the node's FUNCTION method
                func_name = node_cls.FUNCTION
                func = getattr(node, func_name, None)
                if func is None:
                    raise ExecutionError(
                        node_id, node_type,
                        AttributeError(f"Method '{func_name}' not found on {node_type}")
                    )

                result = func(**inputs)

                # Support async node functions
                if asyncio.iscoroutine(result):
                    result = await result

                # Ensure result is a dict
                if not isinstance(result, dict):
                    # Wrap non-dict returns using RETURN_TYPES keys
                    return_types = node_cls.RETURN_TYPES()
                    if isinstance(result, tuple):
                        result = dict(zip(return_types.keys(), result))
                    elif len(return_types) == 1:
                        key = next(iter(return_types))
                        result = {key: result}
                    else:
                        result = {"_result": result}

                node_outputs[node_id] = result

                elapsed = time.time() - start_time
                logger.info(
                    f"Node '{node_id}' ({node_type}) completed in {elapsed:.2f}s, "
                    f"outputs: {list(result.keys())}"
                )

                if on_node_end:
                    on_node_end(node_id, node_type, result)

            except ExecutionError:
                raise
            except Exception as e:
                logger.error(
                    f"Node '{node_id}' ({node_type}) failed:\n"
                    f"{traceback.format_exc()}"
                )
                raise ExecutionError(node_id, node_type, e) from e

        logger.info(f"Workflow '{workflow.name}' execution completed")
        return node_outputs

    def execute_sync(
        self,
        workflow: Workflow,
        runtime_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Synchronous wrapper for execute(). Used in Celery workers."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an already-running loop (e.g. Celery thread)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.execute(workflow, runtime_inputs)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.execute(workflow, runtime_inputs)
                )
        except RuntimeError:
            return asyncio.run(self.execute(workflow, runtime_inputs))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _topological_sort(workflow: Workflow) -> List[NodeInstance]:
        """
        Kahn's algorithm for topological sorting.
        Returns nodes in execution order (dependencies first).
        Skips __runtime__ virtual node (handled separately).
        """
        # Build adjacency and in-degree
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {}
        node_map: Dict[str, NodeInstance] = {}

        for node in workflow.nodes:
            node_map[node.id] = node
            in_degree[node.id] = 0

        for edge in workflow.edges:
            # Skip __runtime__ edges in adjacency but account for in-degree
            if edge.source_id == "__runtime__":
                # __runtime__ doesn't add to real node in-degree
                # (runtime inputs are injected before execution)
                continue
            adj[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        # BFS with queue
        queue = deque(
            nid for nid in in_degree if in_degree[nid] == 0
        )
        order: List[NodeInstance] = []

        while queue:
            nid = queue.popleft()
            if nid in node_map:
                order.append(node_map[nid])
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(workflow.nodes):
            raise WorkflowValidationError(
                ["Workflow contains a cycle (topological sort failed)"]
            )

        return order

    @staticmethod
    def _gather_inputs(
        node: NodeInstance,
        workflow: Workflow,
        node_outputs: Dict[str, Dict[str, Any]],
        node_cls: type,
    ) -> Dict[str, Any]:
        """
        Collect inputs for a node from:
        1. User-configured parameters (from node.parameters)
        2. Upstream node outputs (via edges)
        3. Runtime inputs (from __runtime__)
        """
        inputs: Dict[str, Any] = {}

        # 1. Start with user parameters
        inputs.update(node.parameters)

        # 2. Apply defaults for missing parameters
        defaults = node_cls.get_default_params()
        for key, default_val in defaults.items():
            if key not in inputs:
                inputs[key] = default_val

        # 3. Override with upstream outputs (edges take priority)
        for edge in workflow.get_incoming_edges(node.id):
            source_outputs = node_outputs.get(edge.source_id)
            if source_outputs is None:
                continue

            value = source_outputs.get(edge.source_output)
            if value is not None:
                # Auto-widen IMAGE -> IMAGE_LIST
                target_type = node_cls.get_input_type(edge.target_input)
                if target_type == PortType.IMAGE_LIST and not isinstance(value, list):
                    value = [value]

                inputs[edge.target_input] = value

        # 4. Check runtime inputs for any matching port names
        runtime = node_outputs.get("__runtime__", {})
        for key, value in runtime.items():
            if key in node_cls.get_input_port_names() and key not in inputs:
                inputs[key] = value

        # 5. Remove keys that are not valid input ports
        valid_ports = set(node_cls.get_input_port_names())
        # Also keep parameter keys (widget params are not ports)
        param_keys = set(node_cls.get_default_params().keys())
        valid_keys = valid_ports | param_keys

        filtered = {k: v for k, v in inputs.items() if k in valid_keys}
        return filtered
