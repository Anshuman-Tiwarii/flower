import time
from tornado import web

from ..views import BaseHandler


class TaskProgressHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get enhanced progress data for a specific task"""
        events_state = self.application.events.state
        progress_data = events_state.task_progress.get(task_id, {})
        task = events_state.tasks.get(task_id)

        task_info = {}
        if task:
            task_info = {
                "name": getattr(task, "name", ""),
                "state": getattr(task, "state", "UNKNOWN"),
                "started": getattr(task, "started", None),
                "received": getattr(task, "received", None),
            }

        self.write(
            {
                "task_id": task_id,
                "task_info": task_info,
                "current_progress": progress_data,
                "has_progress": bool(progress_data),
                "has_custom_progress": bool(progress_data),
                "last_updated": time.time(),
            }
        )


class TaskHierarchyHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get hierarchy data for task visualization"""
        events_state = self.application.events.state
        hierarchy = self._build_hierarchy_tree(task_id, events_state)

        self.write(
            {
                "task_id": task_id,
                "hierarchy": hierarchy,
                "has_hierarchy": hierarchy is not None,
            }
        )

    def _build_hierarchy_tree(self, root_task_id, events_state):
        """Build hierarchical tree structure for visualization"""

        def get_task_info(task_id):
            task = events_state.tasks.get(task_id)
            hierarchy_info = events_state.task_hierarchies.get(task_id, {})
            progress_info = events_state.task_progress.get(task_id, {})

            if not task:
                return {
                    "id": task_id,
                    "name": "Unknown Task",
                    "state": "UNKNOWN",
                    "task_type": hierarchy_info.get("task_type", "unknown"),
                    "progress_percent": 0,
                    "children": [],
                }

            worker = getattr(task, "worker", {})
            worker_hostname = worker.hostname if hasattr(worker, "hostname") else None

            return {
                "id": task_id,
                "name": getattr(task, "name", "Unknown"),
                "state": getattr(task, "state", "UNKNOWN"),
                "started": getattr(task, "started", None),
                "runtime": getattr(task, "runtime", None),
                "worker": worker_hostname,
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

        def build_tree(task_id, visited=None):
            if visited is None:
                visited = set()

            if (
                task_id in visited or len(visited) > 10
            ):  # Prevent cycles and limit depth
                return None

            visited.add(task_id)
            task_info = get_task_info(task_id)

            hierarchy_data = events_state.task_hierarchies.get(task_id, {})
            children_ids = hierarchy_data.get("children", [])

            children = []
            for child_id in children_ids:
                child_tree = build_tree(child_id, visited.copy())
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

        task_state = getattr(task, "state", "UNKNOWN")
        has_failed = task_state in ["FAILURE", "REVOKED"]
        failure_metadata = events_state.task_failure_metadata.get(task_id, {})
        failed_subtasks = self._collect_failed_subtasks(task_id, events_state)

        failure_data = {
            "task_id": task_id,
            "has_failed": has_failed,
            "has_failure_analysis": has_failed
            or bool(failure_metadata)
            or bool(failed_subtasks),
            "state": task_state,
            "exception": getattr(task, "exception", None),
            "traceback": getattr(task, "traceback", None),
            "retry_count": getattr(task, "retries", 0),
            "custom_failure_metadata": failure_metadata,
            "has_custom_failure_data": bool(failure_metadata),
            "failed_subtasks": failed_subtasks,
            "subtask_failure_count": len(failed_subtasks),
        }

        if failed_subtasks:
            failure_data["subtask_failure_summary"] = self._analyze_subtask_failures(
                failed_subtasks
            )

        self.write(failure_data)

    def _collect_failed_subtasks(self, root_task_id, events_state, visited=None):
        """Recursively collect all failed subtasks in hierarchy"""
        if visited is None:
            visited = set()

        if root_task_id in visited or len(visited) > 20:  # Prevent cycles
            return []

        visited.add(root_task_id)
        failed_subtasks = []

        task = events_state.tasks.get(root_task_id)
        if task and getattr(task, "state", "UNKNOWN") in ["FAILURE", "REVOKED"]:
            failure_metadata = events_state.task_failure_metadata.get(root_task_id, {})
            worker = getattr(task, "worker", {})
            worker_hostname = worker.hostname if hasattr(worker, "hostname") else None

            exception = getattr(task, "exception", "")
            exception_type = exception.split(":")[0] if ":" in exception else "Unknown"

            failed_subtasks.append(
                {
                    "task_id": root_task_id,
                    "task_name": getattr(task, "name", "Unknown Task"),
                    "state": getattr(task, "state", "UNKNOWN"),
                    "failed_at": getattr(task, "failed", None),
                    "timestamp": getattr(task, "timestamp", None),
                    "worker": worker_hostname,
                    "exception": exception,
                    "traceback": getattr(task, "traceback", ""),
                    "retry_count": getattr(task, "retries", 0),
                    "failure_reason": failure_metadata.get("failure_reason", ""),
                    "failure_metadata": failure_metadata.get("failure_metadata", {}),
                    "failure_stage": failure_metadata.get("failure_stage", ""),
                    "error_details": {
                        "exception_type": exception_type,
                        "error_message": exception,
                        "full_traceback": getattr(task, "traceback", ""),
                        "custom_metadata": failure_metadata.get("failure_metadata", {}),
                        "failure_context": {
                            "stage": failure_metadata.get("failure_stage", ""),
                            "reason": failure_metadata.get("failure_reason", ""),
                            "retry_count": getattr(task, "retries", 0),
                            "worker": worker_hostname,
                        },
                    },
                }
            )

        hierarchy_data = events_state.task_hierarchies.get(root_task_id, {})
        children_ids = hierarchy_data.get("children", [])

        for child_id in children_ids:
            child_failures = self._collect_failed_subtasks(
                child_id, events_state, visited.copy()
            )
            failed_subtasks.extend(child_failures)

        return failed_subtasks

    def _analyze_subtask_failures(self, failed_subtasks):
        """Analyze patterns in failed subtasks"""
        if not failed_subtasks:
            return {}

        failure_types = {}
        failure_stages = {}
        workers_affected = set()

        for subtask in failed_subtasks:
            exc_type = subtask["error_details"].get("exception_type", "Unknown")
            failure_types[exc_type] = failure_types.get(exc_type, 0) + 1

            stage = subtask.get("failure_stage", "unknown")
            failure_stages[stage] = failure_stages.get(stage, 0) + 1

            if subtask.get("worker"):
                workers_affected.add(subtask["worker"])

        return {
            "total_failed_subtasks": len(failed_subtasks),
            "failure_types": failure_types,
            "failure_stages": failure_stages,
            "workers_affected": list(workers_affected),
            "worker_count": len(workers_affected),
            "most_common_failure": (
                max(failure_types.items(), key=lambda x: x[1])[0]
                if failure_types
                else "Unknown"
            ),
            "most_common_stage": (
                max(failure_stages.items(), key=lambda x: x[1])[0]
                if failure_stages
                else "unknown"
            ),
        }


class TaskMetadataHandler(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        """Get comprehensive task metadata including custom data"""
        events_state = self.application.events.state

        task = events_state.tasks.get(task_id)
        progress_data = events_state.task_progress.get(task_id, {})
        hierarchy_data = events_state.task_hierarchies.get(task_id, {})
        failure_data = events_state.task_failure_metadata.get(task_id, {})

        metadata = {
            "task_id": task_id,
            "basic_info": {},
            "progress": progress_data,
            "hierarchy": hierarchy_data,
            "failure_metadata": failure_data,
            "has_enhanced_monitoring": bool(
                progress_data or hierarchy_data or failure_data
            ),
            "monitoring_types": [],
        }

        if task:
            worker = getattr(task, "worker", {})
            worker_hostname = worker.hostname if hasattr(worker, "hostname") else None

            metadata["basic_info"] = {
                "name": getattr(task, "name", ""),
                "state": getattr(task, "state", "UNKNOWN"),
                "started": getattr(task, "started", None),
                "received": getattr(task, "received", None),
                "runtime": getattr(task, "runtime", None),
                "worker": worker_hostname,
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
