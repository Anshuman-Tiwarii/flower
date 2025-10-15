/*
 * Enhanced Task Monitoring JavaScript
 * Provides real-time updates and visualizations for enhanced task monitoring
 * Updated: Details buttons now use success green color
 */

var EnhancedTaskMonitoring = (function () {
    "use strict";

    var taskId;
    var updateInterval;
    var hierarchyChart;

    // URL prefix function (from flower.js)
    function url_prefix() {
        var prefix = $('#url_prefix').val();
        if (prefix) {
            prefix = prefix.replace(/\/+$/, '');
            if (prefix.startsWith('/')) {
                return prefix;
            } else {
                return '/' + prefix;
            }
        }
        return '';
    }

    function init() {
        taskId = $('#taskid').text();
        if (!taskId) {
            console.log('No task ID found, enhanced monitoring disabled');
            return;
        }
        
        // Initialize all tabs
        initializeProgressTab();
        initializeHierarchyTab();
        initializeFailureAnalysisTab();
        
        // Check if task has enhanced monitoring data
        checkEnhancedMonitoringStatus();
        
        // Start real-time updates
        startRealTimeUpdates();
        
        // Setup tab event handlers
        setupTabHandlers();
    }

    function checkEnhancedMonitoringStatus() {
        $.ajax({
            url: url_prefix() + '/api/task/' + taskId + '/metadata',
            method: 'GET',
            success: function(data) {
                if (data.has_enhanced_monitoring) {
                    $('#enhanced-monitoring-badge').removeClass('d-none');
                } else {
                    console.log('No enhanced monitoring data available for task:', taskId);
                    showNoEnhancedDataMessage();
                }
            },
            error: function(xhr, status, error) {
                console.log('Error checking enhanced monitoring status:', error);
                showNoEnhancedDataMessage();
            }
        });
    }

    function showNoEnhancedDataMessage() {
        $('#progress-container').html('<div class="alert alert-info">No enhanced progress data available for this task.</div>');
        $('#hierarchy-container').html('<div class="alert alert-info">No hierarchy data available for this task.</div>');
        $('#failure-analysis-container').html('<div class="alert alert-info">No enhanced failure analysis available for this task.</div>');
    }

    function initializeProgressTab() {
        loadProgressData();
    }

    function loadProgressData() {
        $.ajax({
            url: url_prefix() + '/api/task/' + taskId + '/progress',
            method: 'GET',
            success: function(data) {
                renderProgressDisplay(data);
            },
            error: function(xhr, status, error) {
                console.log('Error loading progress data:', error);
                $('#progress-container').html('<div class="alert alert-warning">Unable to load progress data</div>');
            }
        });
    }

    function renderProgressDisplay(data) {
        var container = $('#progress-container');
        container.empty();

        if (!data.has_custom_progress) {
            container.html('<div class="alert alert-info">No custom progress data available for this task</div>');
            return;
        }

        // Stop polling if task is completed
        var taskState = data.task_info && data.task_info.state;
        if (taskState && (taskState === 'SUCCESS' || taskState === 'FAILURE' || taskState === 'REVOKED')) {
            stopRealTimeUpdates();
        }

        var progress = data.current_progress;
        var progressHtml = '';

        // Main progress bar
        if (progress.progress_percent !== undefined) {
            progressHtml += `
                <div class="mb-4">
                    <h6>${progress.stage || 'Processing'}</h6>
                    <div class="progress mb-2" style="height: 25px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" 
                             style="width: ${progress.progress_percent}%" 
                             aria-valuenow="${progress.progress_percent}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${progress.progress_percent.toFixed(1)}%
                        </div>
                    </div>
                    <small class="text-muted">${progress.status || 'No status message'}</small>
                </div>
            `;
        }

        // Chain progress (for sequential tasks)
        if (progress.current_step && progress.total_steps) {
            progressHtml += `
                <div class="mb-4">
                    <h6>Pipeline Progress</h6>
                    <div class="progress mb-2" style="height: 20px;">
                        <div class="progress-bar bg-success" 
                             style="width: ${(progress.current_step / progress.total_steps) * 100}%">
                            Step ${progress.current_step} of ${progress.total_steps}
                        </div>
                    </div>
                    <small class="text-muted">Current stage: ${progress.current_stage_name || 'Unknown'}</small>
                </div>
            `;
        }

        // Stage progress (for tasks with stages)
        if (progress.stage_progress !== undefined && progress.stage_progress > 0) {
            progressHtml += `
                <div class="mb-4">
                    <h6>Current Stage Progress</h6>
                    <div class="progress mb-2">
                        <div class="progress-bar bg-info" 
                             style="width: ${progress.stage_progress}%">
                            ${progress.stage_progress.toFixed(1)}%
                        </div>
                    </div>
                    <small class="text-muted">${progress.stage_description || 'Processing current stage'}</small>
                </div>
            `;
        }


        container.html(progressHtml);

        // Render subtask summary
        renderSubtaskSummary(progress);
        
        // Update failure analysis tab badge if there are failed subtasks
        updateFailureTabBadge(progress);
    }

    function renderSubtaskSummary(progress) {
        var container = $('#subtask-summary-container');
        
        if (progress.subtasks_created > 0) {
            var completionRate = progress.subtasks_created > 0 ? 
                (progress.subtasks_completed / progress.subtasks_created * 100) : 0;
            var failureRate = progress.subtasks_created > 0 ? 
                (progress.subtasks_failed / progress.subtasks_created * 100) : 0;

            var summaryHtml = `
                <div class="mb-3">
                    <h6>Subtask Overview</h6>
                    <div class="row text-center">
                        <div class="col-3">
                            <div class="border rounded p-2">
                                <div class="h5 text-primary">${progress.subtasks_created}</div>
                                <small>Created</small>
                            </div>
                        </div>
                        <div class="col-3">
                            <div class="border rounded p-2">
                                <div class="h5 text-success">${progress.subtasks_completed}</div>
                                <small>Completed</small>
                            </div>
                        </div>
                        <div class="col-3">
                            <div class="border rounded p-2">
                                <div class="h5 text-danger">${progress.subtasks_failed}</div>
                                <small>Failed</small>
                            </div>
                        </div>
                        <div class="col-3">
                            <div class="border rounded p-2">
                                <div class="h5 text-warning">${progress.subtasks_remaining || 0}</div>
                                <small>Remaining</small>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mb-2">
                    <small>Completion Rate</small>
                    <div class="progress">
                        <div class="progress-bar bg-success" style="width: ${completionRate}%"></div>
                        <div class="progress-bar bg-danger" style="width: ${failureRate}%"></div>
                    </div>
                    <small class="text-muted">${completionRate.toFixed(1)}% complete, ${failureRate.toFixed(1)}% failed</small>
                </div>
            `;
            container.html(summaryHtml);
        } else {
            container.html('<p class="text-muted">No subtask data available</p>');
        }
    }


    function updateFailureTabBadge(progress) {
        var failedCount = progress.subtasks_failed || 0;
        var failureTab = $('#failure-tab');
        
        // Remove existing badge
        failureTab.find('.badge').remove();
        
        // Add badge if there are failures
        if (failedCount > 0) {
            failureTab.append(` <span class="badge bg-danger">${failedCount}</span>`);
        }
    }

    function initializeHierarchyTab() {
        // Load hierarchy data immediately and also when tab is shown
        loadHierarchyData();
        
        // Also reload when tab is clicked (in case data has changed)
        $('#hierarchy-tab').on('shown.bs.tab', function() {
            loadHierarchyData();
        });
    }

    function loadHierarchyData() {
        // Preserve current expanded state before refresh
        var expandedStates = {};
        $('.task-children').each(function() {
            var parentId = $(this).data('parent-id');
            expandedStates[parentId] = $(this).hasClass('expanded');
        });

        $.ajax({
            url: url_prefix() + '/api/task/' + taskId + '/hierarchy',
            method: 'GET',
            success: function(data) {
                renderHierarchyVisualization(data);
                
                // Check if hierarchy is complete (all tasks finished)
                if (data.hierarchy && isHierarchyComplete(data.hierarchy)) {
                    stopRealTimeUpdates();
                }
                
                // Restore expanded states after re-render
                setTimeout(function() {
                    for (var parentId in expandedStates) {
                        if (expandedStates[parentId]) {
                            $('.task-children[data-parent-id="' + parentId + '"]').addClass('expanded');
                            $('.expand-icon[data-task-id="' + parentId + '"]').addClass('expanded');
                        }
                    }
                }, 10); // Small delay to ensure DOM is updated
            },
            error: function(xhr, status, error) {
                console.log('Error loading hierarchy data:', error);
                $('#hierarchy-container').html('<div class="alert alert-warning">Unable to load hierarchy data</div>');
            }
        });
    }

    function renderHierarchyVisualization(data) {
        var container = $('#hierarchy-container');
        
        if (!data.has_hierarchy || !data.hierarchy) {
            container.html('<div class="alert alert-info">This task has no hierarchy relationships</div>');
            return;
        }

        var task = data.hierarchy;
        
        // Better messaging for different scenarios
        if (task.children.length === 0 && task.depth > 0) {
            // This is a leaf subtask
            var messageHtml = `
                <div class="alert alert-info mb-3">
                    <strong>Subtask Information:</strong><br>
                    This is a subtask at depth ${task.depth} with no child tasks.<br>
                    <small>Task Type: ${task.task_type}</small>
                </div>
            `;
            container.html(messageHtml + renderSingleTaskDisplay(task));
            return;
        } else if (task.children.length === 0 && task.depth === 0) {
            // Root task with no children
            var messageHtml = `
                <div class="alert alert-info mb-3">
                    <strong>Single Task:</strong><br>
                    This task has no child tasks or subtasks.
                </div>
            `;
            container.html(messageHtml + renderSingleTaskDisplay(task));
            return;
        }

        // Add expand/collapse controls
        var controlsHtml = `
            <div class="hierarchy-controls mb-3">
                <button type="button" class="btn btn-outline-primary btn-sm" id="expand-all-btn">
                    <i class="fas fa-expand-arrows-alt"></i> Expand All
                </button>
                <button type="button" class="btn btn-outline-secondary btn-sm ms-2" id="collapse-all-btn">
                    <i class="fas fa-compress-arrows-alt"></i> Collapse All
                </button>
                <small class="text-muted ms-3">Click ▶ icons to expand individual tasks.</small>
            </div>
        `;

        // Create collapsible tree visualization
        var treeHtml = renderCollapsibleTaskTree(data.hierarchy, 0, true); // true = is root
        container.html(`
            ${controlsHtml}
            <div class="task-tree">
                ${treeHtml}
            </div>
            <style>
                .task-tree {
                    font-family: monospace;
                    line-height: 1.6;
                    overflow-x: auto;
                    max-width: 100%;
                    white-space: nowrap;
                }
                .task-node {
                    margin: 5px 0;
                    padding: 8px;
                    border-left: 3px solid #ccc;
                    background: #f8f9fa;
                    border-radius: 3px;
                    position: relative;
                    white-space: normal;
                    word-wrap: break-word;
                }
                .task-node.depth-0 { padding-left: 8px; border-color: #007bff; }
                .task-node.depth-1 { padding-left: 24px; border-color: #28a745; }
                .task-node.depth-2 { padding-left: 40px; border-color: #ffc107; }
                .task-node.depth-3 { padding-left: 56px; border-color: #dc3545; }
                .task-node.state-SUCCESS { background-color: #d4edda; }
                .task-node.state-FAILURE { background-color: #f8d7da; }
                .task-node.state-STARTED { background-color: #d1ecf1; }
                .task-node:hover { background-color: #e9ecef; }
                .task-node.expandable { cursor: pointer; }
                .task-node.expandable:hover { background-color: #e9ecef; }
                .task-progress-mini {
                    width: 100px;
                    height: 8px;
                    background: #e9ecef;
                    border-radius: 4px;
                    overflow: hidden;
                    display: inline-block;
                    margin-left: 10px;
                }
                .task-progress-mini .progress-fill {
                    height: 100%;
                    background: #007bff;
                    transition: width 0.3s ease;
                }
                .expand-icon {
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    margin-right: 8px;
                    text-align: center;
                    cursor: pointer;
                    font-size: 12px;
                    vertical-align: middle;
                }
                .expand-icon:before {
                    content: "▶";
                    color: #6c757d;
                }
                .expand-icon.expanded:before {
                    content: "▼";
                    color: #007bff;
                }
                .task-children {
                    display: none;
                    border-left: 1px dashed #dee2e6;
                    margin-left: 12px;
                    padding-left: 4px;
                }
                .task-children.expanded {
                    display: block;
                }
                .hierarchy-controls {
                    border-bottom: 1px solid #dee2e6;
                    padding-bottom: 10px;
                }
            </style>
        `);

        // Setup expand/collapse event handlers
        setupHierarchyEventHandlers();
    }

    function renderTaskTree(node, depth) {
        if (!node) return '';
        
        var progressBar = '';
        if (node.progress_percent > 0) {
            progressBar = `
                <div class="task-progress-mini">
                    <div class="progress-fill" style="width: ${node.progress_percent}%"></div>
                </div>
                <small>(${node.progress_percent.toFixed(1)}%)</small>
            `;
        }

        var subtaskInfo = '';
        if (node.subtasks_created > 0) {
            subtaskInfo = `<small class="text-muted"> | ${node.subtasks_completed}/${node.subtasks_created} subtasks</small>`;
        }

        var chainInfo = '';
        if (node.current_step && node.total_steps) {
            chainInfo = `<small class="text-muted"> | Step ${node.current_step}/${node.total_steps}</small>`;
        }

        var nodeHtml = `
            <div class="task-node depth-${depth} state-${node.state}" onclick="EnhancedTaskMonitoring.navigateToTask('${node.id}')">
                <strong>${node.name}</strong>
                <span class="badge bg-${getStateBadgeClass(node.state)} ms-2">${node.state}</span>
                ${progressBar}
                ${subtaskInfo}
                ${chainInfo}
                <br>
                <small class="text-muted">ID: ${node.id}</small>
                ${node.worker ? `<small class="text-muted"> | Worker: ${node.worker}</small>` : ''}
                ${node.runtime ? `<small class="text-muted"> | Runtime: ${node.runtime.toFixed(2)}s</small>` : ''}
            </div>
        `;

        // Add children
        if (node.children && node.children.length > 0) {
            for (var i = 0; i < node.children.length; i++) {
                nodeHtml += renderTaskTree(node.children[i], depth + 1);
            }
        }

        return nodeHtml;
    }

    function renderSingleTaskDisplay(task) {
        var progressBar = '';
        if (task.progress_percent > 0) {
            progressBar = `
                <div class="task-progress-mini">
                    <div class="progress-fill" style="width: ${task.progress_percent}%; background: #28a745;"></div>
                </div>
                <small>(${task.progress_percent.toFixed(1)}%)</small>
            `;
        }

        return `
            <div class="task-node depth-${task.depth} state-${task.state}" onclick="EnhancedTaskMonitoring.navigateToTask('${task.id}')">
                <strong>${task.name}</strong>
                <span class="badge bg-${getStateBadgeClass(task.state)} ms-2">${task.state}</span>
                ${progressBar}
                <br>
                <small class="text-muted">ID: ${task.id}</small>
                ${task.worker ? `<small class="text-muted"> | Worker: ${task.worker}</small>` : ''}
                ${task.runtime ? `<small class="text-muted"> | Runtime: ${task.runtime.toFixed(2)}s</small>` : ''}
            </div>
        `;
    }

    function getStateBadgeClass(state) {
        switch(state) {
            case 'SUCCESS': return 'success';
            case 'FAILURE': return 'danger';
            case 'STARTED': return 'primary';
            case 'PENDING': return 'secondary';
            case 'RECEIVED': return 'info';
            case 'RETRY': return 'warning';
            default: return 'secondary';
        }
    }

    function navigateToTask(taskId) {
        if (taskId && taskId !== $('#taskid').text()) {
            window.location.href = url_prefix() + '/task/' + encodeURIComponent(taskId);
        }
    }

    function renderCollapsibleTaskTree(node, depth, isRoot) {
        if (!node) return '';
        
        var progressBar = '';
        if (node.progress_percent > 0) {
            progressBar = `
                <div class="task-progress-mini">
                    <div class="progress-fill" style="width: ${node.progress_percent}%"></div>
                </div>
                <small>(${node.progress_percent.toFixed(1)}%)</small>
            `;
        }

        var subtaskInfo = '';
        if (node.subtasks_created > 0) {
            subtaskInfo = `<small class="text-muted"> | ${node.subtasks_completed}/${node.subtasks_created} subtasks</small>`;
        }

        var chainInfo = '';
        if (node.current_step && node.total_steps) {
            chainInfo = `<small class="text-muted"> | Step ${node.current_step}/${node.total_steps}</small>`;
        }

        var hasChildren = node.children && node.children.length > 0;
        var expandIcon = hasChildren ? '<span class="expand-icon" data-task-id="' + node.id + '"></span>' : '<span style="width: 16px; display: inline-block;"></span>';
        var expandableClass = hasChildren ? ' expandable' : '';

        var nodeHtml = `
            <div class="task-node depth-${depth} state-${node.state}${expandableClass}" data-task-id="${node.id}">
                ${expandIcon}
                <span onclick="EnhancedTaskMonitoring.navigateToTask('${node.id}')">
                    <strong>${node.name}</strong>
                    <span class="badge bg-${getStateBadgeClass(node.state)} ms-2">${node.state}</span>
                    ${progressBar}
                    ${subtaskInfo}
                    ${chainInfo}
                    <br>
                    <small class="text-muted">ID: ${node.id}</small>
                    ${node.worker ? `<small class="text-muted"> | Worker: ${node.worker}</small>` : ''}
                    ${node.runtime ? `<small class="text-muted"> | Runtime: ${node.runtime.toFixed(2)}s</small>` : ''}
                </span>
            </div>
        `;

        // Add children container (collapsed by default for all nodes)
        if (hasChildren) {
            var childrenClass = 'task-children';  // All collapsed by default
            nodeHtml += `<div class="${childrenClass}" data-parent-id="${node.id}">`;
            
            for (var i = 0; i < node.children.length; i++) {
                nodeHtml += renderCollapsibleTaskTree(node.children[i], depth + 1, false);
            }
            
            nodeHtml += '</div>';
        }

        return nodeHtml;
    }

    function setupHierarchyEventHandlers() {
        // Individual node expand/collapse
        $(document).off('click', '.expand-icon').on('click', '.expand-icon', function(e) {
            e.stopPropagation();
            var taskId = $(this).data('task-id');
            var childrenContainer = $('.task-children[data-parent-id="' + taskId + '"]');
            var icon = $(this);
            
            if (childrenContainer.hasClass('expanded')) {
                childrenContainer.removeClass('expanded');
                icon.removeClass('expanded');
            } else {
                childrenContainer.addClass('expanded');
                icon.addClass('expanded');
            }
        });

        // Expand all button
        $(document).off('click', '#expand-all-btn').on('click', '#expand-all-btn', function() {
            $('.task-children').addClass('expanded');
            $('.expand-icon').addClass('expanded');
        });

        // Collapse all button - collapse everything
        $(document).off('click', '#collapse-all-btn').on('click', '#collapse-all-btn', function() {
            $('.task-children').removeClass('expanded');
            $('.expand-icon').removeClass('expanded');
        });
    }

    function initializeFailureAnalysisTab() {
        $('#failure-tab').one('shown.bs.tab', function() {
            loadFailureAnalysis();
        });
    }

    function loadFailureAnalysis() {
        $.ajax({
            url: url_prefix() + '/api/task/' + taskId + '/failure-analysis',
            method: 'GET',
            success: function(data) {
                renderFailureAnalysis(data);
            },
            error: function(xhr, status, error) {
                console.log('Error loading failure analysis:', error);
                $('#failure-analysis-container').html('<div class="alert alert-warning">Unable to load failure analysis</div>');
            }
        });
    }

    function renderFailureAnalysis(data) {
        var container = $('#failure-analysis-container');
        
        if (!data.has_failed && (!data.failed_subtasks || data.failed_subtasks.length === 0)) {
            container.html('<div class="alert alert-success"><i class="fas fa-check-circle"></i> Task and all subtasks completed successfully</div>');
            return;
        }

        var failureHtml = '';

        // Render main task failure if it exists
        if (data.has_failed) {
            failureHtml += `
                <div class="alert alert-danger">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6><i class="fas fa-exclamation-triangle"></i> Main Task Failed</h6>
                            <strong>State:</strong> ${data.state}<br>
                            <strong>Exception:</strong> ${data.exception || 'Unknown error'}<br>
                            <strong>Retry Count:</strong> ${data.retry_count || 0}
                        </div>
                        ${data.traceback || data.custom_failure_metadata ? `
                            <button class="btn btn-outline-light btn-sm" 
                                    type="button" 
                                    onclick="toggleMainTaskErrorDetails()" 
                                    id="main-task-toggle">
                                <i class="fas fa-eye"></i> Details
                            </button>
                        ` : ''}
                    </div>
                    
                    ${data.traceback || data.custom_failure_metadata ? `
                        <div class="collapse mt-3" id="main-task-details">
                            <div class="card bg-light">
                                <div class="card-header">
                                    <h6 class="mb-0"><i class="fas fa-bug"></i> Main Task Error Details</h6>
                                </div>
                                <div class="card-body">
                                    ${data.custom_failure_metadata && Object.keys(data.custom_failure_metadata).length > 0 ? `
                                        <div class="mb-3">
                                            <h6 class="text-primary">Custom Metadata</h6>
                                            <div class="json-viewer">
                                                <pre class="bg-white border rounded p-2" style="max-height: 200px; overflow-y: auto; font-size: 0.85em;">${JSON.stringify(data.custom_failure_metadata, null, 2)}</pre>
                                            </div>
                                        </div>
                                    ` : ''}
                                    
                                    ${data.traceback ? `
                                        <div class="mt-3">
                                            <h6 class="text-primary">Full Traceback</h6>
                                            <pre class="bg-dark text-light p-3 rounded" style="max-height: 300px; overflow-y: auto; font-size: 0.8em;">${data.traceback}</pre>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Render failed subtasks section
        if (data.failed_subtasks && data.failed_subtasks.length > 0) {
            failureHtml += renderFailedSubtasksSection(data);
        }

        container.html(failureHtml);
        
        // Setup event handlers for expandable subtask details
        setupSubtaskFailureHandlers();
    }


    function renderFailedSubtasksSection(data) {
        if (!data.failed_subtasks || data.failed_subtasks.length === 0) {
            return '';
        }

        var subtaskHtml = `
            <div class="mt-4">
                <div class="card border-danger">
                    <div class="card-header bg-danger text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-times-circle"></i> Failed Subtasks 
                            <span class="badge bg-light text-dark">${data.failed_subtasks.length}</span>
                        </h5>
                        ${data.subtask_failure_summary ? renderFailureSummary(data.subtask_failure_summary) : ''}
                    </div>
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush">
        `;

        data.failed_subtasks.forEach(function(subtask, index) {
            subtaskHtml += renderFailedSubtaskItem(subtask, index);
        });

        subtaskHtml += `
                        </div>
                    </div>
                </div>
            </div>
        `;

        return subtaskHtml;
    }

    function renderFailureSummary(summary) {
        return `
            <div class="mt-2">
                <small class="d-block">
                    <strong>Summary:</strong> ${summary.total_failed_subtasks} failed subtasks across ${summary.worker_count} workers
                </small>
                <small class="d-block">
                    <strong>Most Common:</strong> ${summary.most_common_failure} (${summary.failure_types[summary.most_common_failure] || 0} occurrences)
                </small>
            </div>
        `;
    }

    function renderFailedSubtaskItem(subtask, index) {
        var timeStr = '';
        if (subtask.failed_at) {
            timeStr = moment.unix(subtask.failed_at).format('YYYY-MM-DD HH:mm:ss');
        } else if (subtask.timestamp) {
            timeStr = moment.unix(subtask.timestamp).format('YYYY-MM-DD HH:mm:ss');
        }

        var errorPreview = subtask.exception || subtask.failure_reason || 'Unknown error';
        if (errorPreview.length > 100) {
            errorPreview = errorPreview.substring(0, 100) + '...';
        }

        return `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <a href="${url_prefix()}/task/${subtask.task_id}" class="text-decoration-none">
                                ${subtask.task_name}
                            </a>
                            <span class="badge bg-danger ms-2">${subtask.state}</span>
                            ${subtask.retry_count > 0 ? `<span class="badge bg-warning text-dark ms-1">Retry ${subtask.retry_count}</span>` : ''}
                        </h6>
                        <p class="mb-1 text-muted">
                            <small>
                                <i class="fas fa-exclamation-triangle text-danger"></i>
                                <strong>Error:</strong> ${errorPreview}
                            </small>
                        </p>
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-clock"></i> ${timeStr || 'Time unknown'}
                                ${subtask.worker ? `<span class="ms-2"><i class="fas fa-server"></i> ${subtask.worker}</span>` : ''}
                                ${subtask.failure_stage ? `<span class="ms-2"><i class="fas fa-layer-group"></i> Stage: ${subtask.failure_stage}</span>` : ''}
                            </small>
                        </div>
                    </div>
                    <div>
                        <button class="btn btn-outline-success btn-sm" 
                                type="button" 
                                onclick="toggleSubtaskErrorDetails(${index})" 
                                id="subtask-toggle-${index}">
                            <i class="fas fa-eye"></i> Details
                        </button>
                    </div>
                </div>
                
                <!-- Expandable Error Details -->
                <div class="collapse mt-3" id="subtask-details-${index}">
                    <div class="card bg-light">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="fas fa-bug"></i> Detailed Error Information</h6>
                        </div>
                        <div class="card-body">
                            ${renderSubtaskErrorDetails(subtask)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderSubtaskErrorDetails(subtask) {
        var errorDetails = subtask.error_details || {};
        var customMetadata = errorDetails.custom_metadata || {};
        var failureContext = errorDetails.failure_context || {};

        var detailsHtml = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-primary">Exception Information</h6>
                    <table class="table table-sm table-borderless">
                        <tr>
                            <td class="fw-bold">Exception Type:</td>
                            <td><code>${errorDetails.exception_type || 'Unknown'}</code></td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Error Message:</td>
                            <td>${errorDetails.error_message || 'No message available'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Task ID:</td>
                            <td><code>${subtask.task_id}</code></td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Worker:</td>
                            <td>${failureContext.worker || 'Unknown'}</td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Retry Count:</td>
                            <td>${failureContext.retry_count || 0}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-primary">Failure Context</h6>
                    <table class="table table-sm table-borderless">
                        <tr>
                            <td class="fw-bold">Failure Stage:</td>
                            <td><span class="badge bg-secondary">${failureContext.stage || 'Unknown'}</span></td>
                        </tr>
                        <tr>
                            <td class="fw-bold">Failure Reason:</td>
                            <td>${failureContext.reason || 'Not specified'}</td>
                        </tr>
                    </table>
                </div>
            </div>
        `;

        // Add custom metadata if available
        if (Object.keys(customMetadata).length > 0) {
            detailsHtml += `
                <div class="mt-3">
                    <h6 class="text-primary">Custom Metadata</h6>
                    <div class="json-viewer">
                        <pre class="bg-white border rounded p-2" style="max-height: 200px; overflow-y: auto; font-size: 0.85em;">${JSON.stringify(customMetadata, null, 2)}</pre>
                    </div>
                </div>
            `;
        }

        // Add system metrics if available
        var systemMetrics = errorDetails.system_metrics;
        if (systemMetrics) {
            detailsHtml += `
                <div class="mt-3">
                    <h6 class="text-primary">System Metrics (at failure time)</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <table class="table table-sm table-borderless">
                                ${systemMetrics.cpu_percent !== null && systemMetrics.cpu_percent !== undefined ? `
                                    <tr><td class="fw-bold">CPU Usage:</td><td><span class="badge ${systemMetrics.cpu_percent > 80 ? 'bg-danger' : systemMetrics.cpu_percent > 60 ? 'bg-warning' : 'bg-success'}">${systemMetrics.cpu_percent}%</span></td></tr>
                                ` : ''}
                                ${systemMetrics.memory_percent !== null && systemMetrics.memory_percent !== undefined ? `
                                    <tr><td class="fw-bold">Memory Usage:</td><td><span class="badge ${systemMetrics.memory_percent > 90 ? 'bg-danger' : systemMetrics.memory_percent > 80 ? 'bg-warning' : 'bg-success'}">${systemMetrics.memory_percent}%</span></td></tr>
                                ` : ''}
                                ${systemMetrics.memory_available_gb !== null && systemMetrics.memory_available_gb !== undefined ? `
                                    <tr><td class="fw-bold">Available RAM:</td><td>${systemMetrics.memory_available_gb} GB</td></tr>
                                ` : ''}
                                ${systemMetrics.load_average_1min !== null && systemMetrics.load_average_1min !== undefined ? `
                                    <tr><td class="fw-bold">Load Average:</td><td><span class="badge ${systemMetrics.load_average_1min > 2 ? 'bg-danger' : systemMetrics.load_average_1min > 1 ? 'bg-warning' : 'bg-success'}">${systemMetrics.load_average_1min}</span></td></tr>
                                ` : ''}
                            </table>
                        </div>
                        <div class="col-md-6">
                            <table class="table table-sm table-borderless">
                                <tr><td class="fw-bold">Hostname:</td><td><code>${systemMetrics.hostname || 'unknown'}</code></td></tr>
                                ${systemMetrics.redis_status && typeof systemMetrics.redis_status === 'object' ? `
                                    <tr><td class="fw-bold">Redis:</td><td>
                                        ${systemMetrics.redis_status.connected ? 
                                            '<span class="badge bg-success">Connected</span>' : 
                                            '<span class="badge bg-danger">Disconnected</span>'}
                                    </td></tr>
                                    ${systemMetrics.redis_status.memory_used ? `
                                        <tr><td class="fw-bold">Redis Memory:</td><td>${systemMetrics.redis_status.memory_used}</td></tr>
                                    ` : ''}
                                    ${systemMetrics.redis_status.connected_clients !== undefined ? `
                                        <tr><td class="fw-bold">Redis Clients:</td><td>${systemMetrics.redis_status.connected_clients}</td></tr>
                                    ` : ''}
                                ` : ''}
                            </table>
                        </div>
                    </div>
                    ${systemMetrics.error ? `
                        <div class="alert alert-warning alert-sm">
                            <small><strong>Note:</strong> ${systemMetrics.error}</small>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Add full traceback if available
        if (errorDetails.full_traceback && errorDetails.full_traceback.trim() !== '') {
            detailsHtml += `
                <div class="mt-3">
                    <h6 class="text-primary">Full Traceback</h6>
                    <pre class="bg-dark text-light p-3 rounded" style="max-height: 300px; overflow-y: auto; font-size: 0.8em;">${errorDetails.full_traceback}</pre>
                </div>
            `;
        }

        return detailsHtml;
    }

    function setupSubtaskFailureHandlers() {
        // Event handlers are set up via onclick attributes in the HTML
        // This function could be used for additional setup if needed
    }

    // Global function for toggling subtask error details
    window.toggleSubtaskErrorDetails = function(index) {
        var detailsElement = $('#subtask-details-' + index);
        var buttonElement = $('#subtask-toggle-' + index);
        var icon = buttonElement.find('i');
        
        if (detailsElement.hasClass('show')) {
            detailsElement.collapse('hide');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
            buttonElement.html('<i class="fas fa-eye"></i> Details');
        } else {
            detailsElement.collapse('show');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
            buttonElement.html('<i class="fas fa-eye-slash"></i> Hide');
        }
    };

    // Global function for toggling main task error details
    window.toggleMainTaskErrorDetails = function() {
        var detailsElement = $('#main-task-details');
        var buttonElement = $('#main-task-toggle');
        var icon = buttonElement.find('i');
        
        if (detailsElement.hasClass('show')) {
            detailsElement.collapse('hide');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
            buttonElement.html('<i class="fas fa-eye"></i> Details');
        } else {
            detailsElement.collapse('show');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
            buttonElement.html('<i class="fas fa-eye-slash"></i> Hide');
        }
    };

    function setupTabHandlers() {
        // Handle tab switching
        $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
            var target = $(e.target).attr("href");
            
            // Trigger specific loading for tabs that need it
            if (target === '#hierarchy' && !hierarchyChart) {
                loadHierarchyData();
            }
        });
    }

    function startRealTimeUpdates() {
        // Update progress data every 3 seconds if progress tab is active
        updateInterval = setInterval(function() {
            if ($('#progress-tab').hasClass('active') || $('#progress').hasClass('active show')) {
                loadProgressData();
            }
            if ($('#hierarchy-tab').hasClass('active') || $('#hierarchy').hasClass('active show')) {
                loadHierarchyData();
            }
        }, 3000);
    }

    function stopRealTimeUpdates() {
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
    }

    function isHierarchyComplete(taskNode) {
        if (!taskNode) return true;
        
        // Check if current task is in a final state
        var finalStates = ['SUCCESS', 'FAILURE', 'REVOKED'];
        var isCurrentTaskComplete = finalStates.includes(taskNode.state);
        
        // If current task is not complete, hierarchy is not complete
        if (!isCurrentTaskComplete) {
            return false;
        }
        
        // Recursively check all children
        if (taskNode.children && taskNode.children.length > 0) {
            for (var i = 0; i < taskNode.children.length; i++) {
                if (!isHierarchyComplete(taskNode.children[i])) {
                    return false; // If any child is not complete, hierarchy is not complete
                }
            }
        }
        
        // Current task and all children are complete
        return true;
    }

    // Public API
    return {
        init: init,
        loadProgressData: loadProgressData,
        loadHierarchyData: loadHierarchyData,
        loadFailureAnalysis: loadFailureAnalysis,
        stopRealTimeUpdates: stopRealTimeUpdates,
        navigateToTask: navigateToTask
    };
})();

// Initialize when document is ready
$(document).ready(function () {
    // Only initialize on task detail pages
    if (window.location.pathname.includes('/task/')) {
        EnhancedTaskMonitoring.init();
    }
});

// Cleanup when leaving the page
$(window).on('beforeunload', function() {
    EnhancedTaskMonitoring.stopRealTimeUpdates();
});