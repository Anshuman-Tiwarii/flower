import time
from tornado import web

from ..views import BaseHandler


class TaskProgressHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get enhanced progress data for a specific task"""
        events_state = self.application.events.state

        # Get progress data
        progress_data = events_state.task_progress.get(task_id, {})

        # Get progress data from current state
        # Note: Historical events are available but not needed by frontend

        # Get task basic info
        task = events_state.tasks.get(task_id)
        task_info = {}
        if task:
            task_info = {
                "name": getattr(task, "name", ""),
                "state": getattr(task, "state", "UNKNOWN"),
                "started": getattr(task, "started", None),
                "received": getattr(task, "received", None),
            }

        response = {
            "task_id": task_id,
            "task_info": task_info,
            "current_progress": progress_data,
            "has_custom_progress": bool(progress_data),
            "last_updated": time.time(),
        }

        self.write(response)


class TaskHierarchyHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get hierarchy data for task visualization"""
        events_state = self.application.events.state

        # Build hierarchy tree
        hierarchy = self.build_hierarchy_tree(task_id, events_state)

        self.write(
            {
                "task_id": task_id,
                "hierarchy": hierarchy,
                "has_hierarchy": hierarchy is not None,
            }
        )

    def build_hierarchy_tree(self, root_task_id, events_state):
        """Build hierarchical tree structure for visualization"""

        def get_task_info(task_id):
            task = events_state.tasks.get(task_id)
            hierarchy_info = events_state.task_hierarchies.get(task_id, {})
            progress_info = events_state.task_progress.get(task_id, {})

            if not task:
                # Return minimal info if task not found but referenced
                return {
                    "id": task_id,
                    "name": "Unknown Task",
                    "state": "UNKNOWN",
                    "task_type": hierarchy_info.get("task_type", "unknown"),
                    "progress_percent": 0,
                    "children": [],
                }

            return {
                "id": task_id,
                "name": getattr(task, "name", "Unknown"),
                "state": getattr(task, "state", "UNKNOWN"),
                "started": getattr(task, "started", None),
                "runtime": getattr(task, "runtime", None),
                "worker": (
                    getattr(task, "worker", {}).hostname
                    if hasattr(getattr(task, "worker", {}), "hostname")
                    else None
                ),
                "task_type": hierarchy_info.get("task_type", "single"),
                "depth": hierarchy_info.get("depth", 0),
                "progress_percent": progress_info.get("progress_percent", 0),
                "subtasks_created": progress_info.get("subtasks_created", 0),
                "subtasks_completed": progress_info.get("subtasks_completed", 0),
                "subtasks_failed": progress_info.get("subtasks_failed", 0),
                "current_step": progress_info.get("current_step"),
                "total_steps": progress_info.get("total_steps"),
                "children": [],
            }

        def build_tree(task_id, visited=None, max_depth=5):
            if visited is None:
                visited = set()

            if task_id in visited or len(visited) > max_depth:
                return None  # Prevent infinite loops and deep recursion

            visited.add(task_id)
            task_info = get_task_info(task_id)

            # Get children from hierarchy data
            hierarchy_data = events_state.task_hierarchies.get(task_id, {})
            children_ids = hierarchy_data.get("children", [])

            # Build children
            children = []
            for child_id in children_ids:
                child_tree = build_tree(child_id, visited.copy(), max_depth)
                if child_tree:
                    children.append(child_tree)

            task_info["children"] = children
            return task_info

        return build_tree(root_task_id)


class TaskFailureAnalysisHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get detailed failure analysis for a task"""
        events_state = self.application.events.state
        task = events_state.tasks.get(task_id)

        if not task:
            raise web.HTTPError(404, f"Task {task_id} not found")

        # Get basic failure info
        task_state = getattr(task, "state", "UNKNOWN")
        has_failed = task_state in ["FAILURE", "REVOKED"]

        # Get custom failure metadata
        failure_metadata = events_state.task_failure_metadata.get(task_id, {})

        # Get failed subtasks across hierarchy
        failed_subtasks = self.collect_failed_subtasks(task_id, events_state)

        # Note: Historical failure events no longer stored (memory optimization)
        # Current failure state is maintained in failure_metadata
        
        failure_data = {
            "task_id": task_id,
            "has_failed": has_failed,
            "state": task_state,
            "exception": getattr(task, "exception", None),
            "traceback": getattr(task, "traceback", None),
            "retry_count": getattr(task, "retries", 0),
            "custom_failure_metadata": failure_metadata,
            "failure_events": [],  # Historical events eliminated for memory optimization
            "has_custom_failure_data": bool(failure_metadata),
            "failed_subtasks": failed_subtasks,
            "subtask_failure_count": len(failed_subtasks),
        }

        # Automated failure analysis removed - not using GPT models

        # Add subtask failure summary
        if failed_subtasks:
            failure_data["subtask_failure_summary"] = self.analyze_subtask_failures(failed_subtasks)

        self.write(failure_data)

    def analyze_failure(self, task, custom_metadata):
        """Provide basic failure analysis"""
        exception = getattr(task, "exception", "") or ""
        traceback = getattr(task, "traceback", "") or ""

        analysis = {
            "exception_type": (
                exception.split(":")[0] if ":" in exception else "Unknown"
            ),
            "likely_causes": [],
            "suggested_actions": [],
            "failure_patterns": [],
        }

        # Simple failure pattern matching
        exception_lower = exception.lower()
        traceback_lower = traceback.lower()

        if "connectionerror" in exception_lower or "connection" in exception_lower:
            analysis["likely_causes"].append("Network connectivity issue")
            analysis["suggested_actions"].append(
                "Check network configuration and service availability"
            )
            analysis["failure_patterns"].append("NETWORK_ERROR")

        if "timeout" in exception_lower or "timeouterror" in exception_lower:
            analysis["likely_causes"].append("Operation timeout")
            analysis["suggested_actions"].append(
                "Increase timeout or optimize task performance"
            )
            analysis["failure_patterns"].append("TIMEOUT_ERROR")

        if "memoryerror" in exception_lower or "memory" in exception_lower:
            analysis["likely_causes"].append("Insufficient memory")
            analysis["suggested_actions"].append(
                "Increase worker memory or optimize memory usage"
            )
            analysis["failure_patterns"].append("MEMORY_ERROR")

        if "permission" in exception_lower or "access" in exception_lower:
            analysis["likely_causes"].append("Permission or access issue")
            analysis["suggested_actions"].append("Check file/resource permissions")
            analysis["failure_patterns"].append("PERMISSION_ERROR")

        # Add custom failure metadata analysis
        if custom_metadata:
            custom_reason = custom_metadata.get("failure_reason", "")
            if custom_reason:
                analysis["likely_causes"].append(f"Custom failure: {custom_reason}")

        return analysis

    def collect_failed_subtasks(self, root_task_id, events_state, visited=None, max_depth=10):
        """Recursively collect all failed subtasks in hierarchy"""
        if visited is None:
            visited = set()
        
        if root_task_id in visited or len(visited) > max_depth:
            return []
        
        visited.add(root_task_id)
        failed_subtasks = []
        
        # Check if current task is failed
        task = events_state.tasks.get(root_task_id)
        if task and getattr(task, "state", "UNKNOWN") in ["FAILURE", "REVOKED"]:
            failure_metadata = events_state.task_failure_metadata.get(root_task_id, {})
            
            failed_subtasks.append({
                "task_id": root_task_id,
                "task_name": getattr(task, "name", "Unknown Task"),
                "state": getattr(task, "state", "UNKNOWN"),
                "failed_at": getattr(task, "failed", None),
                "timestamp": getattr(task, "timestamp", None),
                "worker": getattr(task, "worker", {}).hostname if hasattr(getattr(task, "worker", {}), "hostname") else None,
                "exception": getattr(task, "exception", ""),
                "traceback": getattr(task, "traceback", ""),
                "retry_count": getattr(task, "retries", 0),
                "failure_reason": failure_metadata.get("failure_reason", ""),
                "failure_metadata": failure_metadata.get("failure_metadata", {}),
                "failure_stage": failure_metadata.get("failure_stage", ""),
                "error_details": {
                    "exception_type": getattr(task, "exception", "").split(":")[0] if getattr(task, "exception", "") and ":" in getattr(task, "exception", "") else "Unknown",
                    "error_message": getattr(task, "exception", ""),
                    "full_traceback": getattr(task, "traceback", ""),
                    "custom_metadata": failure_metadata.get("failure_metadata", {}),
                    "system_metrics": failure_metadata.get("system_metrics", {}),
                    "failure_context": {
                        "stage": failure_metadata.get("failure_stage", ""),
                        "reason": failure_metadata.get("failure_reason", ""),
                        "retry_count": getattr(task, "retries", 0),
                        "worker": getattr(task, "worker", {}).hostname if hasattr(getattr(task, "worker", {}), "hostname") else None,
                    }
                }
            })
        
        # Get children from hierarchy data and recursively check them
        hierarchy_data = events_state.task_hierarchies.get(root_task_id, {})
        children_ids = hierarchy_data.get("children", [])
        
        for child_id in children_ids:
            child_failures = self.collect_failed_subtasks(child_id, events_state, visited.copy(), max_depth)
            failed_subtasks.extend(child_failures)
        
        return failed_subtasks
    
    def analyze_subtask_failures(self, failed_subtasks):
        """Analyze patterns in failed subtasks"""
        if not failed_subtasks:
            return {}
        
        failure_types = {}
        failure_stages = {}
        workers_affected = set()
        total_failures = len(failed_subtasks)
        
        for subtask in failed_subtasks:
            # Categorize by exception type
            exc_type = subtask["error_details"].get("exception_type", "Unknown")
            failure_types[exc_type] = failure_types.get(exc_type, 0) + 1
            
            # Categorize by failure stage
            stage = subtask.get("failure_stage", "unknown")
            failure_stages[stage] = failure_stages.get(stage, 0) + 1
            
            # Track affected workers
            if subtask.get("worker"):
                workers_affected.add(subtask["worker"])
        
        return {
            "total_failed_subtasks": total_failures,
            "failure_types": failure_types,
            "failure_stages": failure_stages,
            "workers_affected": list(workers_affected),
            "worker_count": len(workers_affected),
            "most_common_failure": max(failure_types.items(), key=lambda x: x[1])[0] if failure_types else "Unknown",
            "most_common_stage": max(failure_stages.items(), key=lambda x: x[1])[0] if failure_stages else "unknown"
        }


class TaskCustomEventsHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get all custom events for a task"""
        events_state = self.application.events.state

        # Historical events eliminated for memory optimization
        # This endpoint now returns empty event data
        
        self.write(
            {
                "task_id": task_id,
                "total_events": 0,  # Events no longer stored
                "events_by_type": {},  # Events no longer stored
                "all_events": [],  # Events no longer stored
                "note": "Historical events eliminated for memory optimization"
            }
        )


class TaskMetadataHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get comprehensive task metadata including custom data"""
        events_state = self.application.events.state

        # Get all data for the task
        task = events_state.tasks.get(task_id)
        progress_data = events_state.task_progress.get(task_id, {})
        hierarchy_data = events_state.task_hierarchies.get(task_id, {})
        failure_data = events_state.task_failure_metadata.get(task_id, {})
        # Historical events eliminated for memory optimization
        
        # Build comprehensive metadata
        metadata = {
            "task_id": task_id,
            "basic_info": {},
            "progress": progress_data,
            "hierarchy": hierarchy_data,
            "failure_metadata": failure_data,
            "custom_events_count": 0,  # Events no longer stored
            "has_enhanced_monitoring": bool(
                progress_data or hierarchy_data or failure_data
            ),
            "monitoring_types": [],
        }

        # Add basic task info
        if task:
            metadata["basic_info"] = {
                "name": getattr(task, "name", ""),
                "state": getattr(task, "state", "UNKNOWN"),
                "started": getattr(task, "started", None),
                "received": getattr(task, "received", None),
                "runtime": getattr(task, "runtime", None),
                "worker": (
                    getattr(task, "worker", {}).hostname
                    if hasattr(getattr(task, "worker", {}), "hostname")
                    else None
                ),
                "retries": getattr(task, "retries", 0),
            }

        # Determine monitoring types
        if progress_data:
            if progress_data.get("subtasks_created", 0) > 0:
                metadata["monitoring_types"].append("PARENT_WITH_SUBTASKS")
            elif progress_data.get("current_step"):
                metadata["monitoring_types"].append("CHAIN_TASK")
            else:
                metadata["monitoring_types"].append("PROGRESS_TRACKING")

        if hierarchy_data:
            metadata["monitoring_types"].append("HIERARCHY_TRACKING")

        if failure_data:
            metadata["monitoring_types"].append("ENHANCED_FAILURE_TRACKING")

        self.write(metadata)
