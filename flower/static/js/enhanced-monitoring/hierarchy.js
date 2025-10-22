/**
 * Enhanced Task Monitoring - Hierarchy Module
 * Handles task hierarchy visualization and tree navigation
 */

var HierarchyMonitoring = (function () {
    "use strict";

    var isInitialized = false;
    var hierarchyUpdateInterval;

    function init() {
        if (isInitialized) return;
        
        // Initialize hierarchy tab
        initializeHierarchyTab();
        
        // Listen for tab activation events
        $(document).on('enhanced-monitoring:tab-shown', function(e, data) {
            if (data.tab === '#hierarchy') {
                loadHierarchyData();
            }
        });
        
        isInitialized = true;
        console.log('Hierarchy monitoring module initialized');
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
        var expandedStates = preserveExpandedStates();

        EnhancedMonitoringCore.showLoadingMessage('#hierarchy-container', 'Loading hierarchy data...');

        EnhancedMonitoringCore.makeApiRequest('hierarchy', {
            success: function(data) {
                renderHierarchyVisualization(data);
                
                // Check if hierarchy is complete (all tasks finished)
                if (data.hierarchy && isHierarchyComplete(data.hierarchy)) {
                    stopRealTimeUpdates();
                }
                
                // Restore expanded states after re-render
                restoreExpandedStates(expandedStates);
            },
            error: function(xhr, status, error) {
                console.log('Error loading hierarchy data:', error);
                EnhancedMonitoringCore.showErrorMessage('#hierarchy-container', 'Unable to load hierarchy data');
            }
        });
    }

    function preserveExpandedStates() {
        var expandedStates = {};
        $('.task-children').each(function() {
            var parentId = $(this).data('parent-id');
            expandedStates[parentId] = $(this).hasClass('expanded');
        });
        return expandedStates;
    }

    function restoreExpandedStates(expandedStates) {
        setTimeout(function() {
            for (var parentId in expandedStates) {
                if (expandedStates[parentId]) {
                    $('.task-children[data-parent-id="' + parentId + '"]').addClass('expanded');
                    $('.expand-icon[data-task-id="' + parentId + '"]').addClass('expanded');
                }
            }
        }, 10); // Small delay to ensure DOM is updated
    }

    function renderHierarchyVisualization(data) {
        var container = $('#hierarchy-container');
        
        if (!data.has_hierarchy || !data.hierarchy) {
            EnhancedMonitoringCore.showNoDataMessage('#hierarchy-container', 'This task has no hierarchy relationships');
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
        var controlsHtml = renderHierarchyControls();

        // Create collapsible tree visualization
        var treeHtml = renderCollapsibleTaskTree(data.hierarchy, 0, true); // true = is root
        container.html(`
            ${controlsHtml}
            <div class="task-tree">
                ${treeHtml}
            </div>
        `);

        // Setup expand/collapse event handlers
        setupHierarchyEventHandlers();
    }

    function renderHierarchyControls() {
        return `
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
            <div class="task-node depth-${task.depth} state-${task.state}" onclick="EnhancedMonitoringCore.navigateToTask('${task.id}')">
                <strong>${task.name}</strong>
                <span class="badge bg-${EnhancedMonitoringCore.getStateBadgeClass(task.state)} ms-2">${task.state}</span>
                ${progressBar}
                <br>
                <small class="text-muted">ID: ${task.id}</small>
                ${task.worker ? `<small class="text-muted"> | Worker: ${task.worker}</small>` : ''}
                ${task.runtime ? `<small class="text-muted"> | Runtime: ${task.runtime.toFixed(2)}s</small>` : ''}
            </div>
        `;
    }

    function renderCollapsibleTaskTree(node, depth, isRoot) {
        if (!node) return '';
        
        var progressBar = renderProgressBar(node);
        var additionalInfo = renderAdditionalInfo(node);

        var hasChildren = node.children && node.children.length > 0;
        var expandIcon = hasChildren ? '<span class="expand-icon" data-task-id="' + node.id + '"></span>' : '<span style="width: 16px; display: inline-block;"></span>';
        var expandableClass = hasChildren ? ' expandable' : '';

        var nodeHtml = `
            <div class="task-node depth-${depth} state-${node.state}${expandableClass}" data-task-id="${node.id}">
                ${expandIcon}
                <span onclick="EnhancedMonitoringCore.navigateToTask('${node.id}')">
                    <strong>${node.name}</strong>
                    <span class="badge bg-${EnhancedMonitoringCore.getStateBadgeClass(node.state)} ms-2">${node.state}</span>
                    ${progressBar}
                    <br>
                    <small class="text-muted">ID: ${node.id}</small>
                    ${node.worker ? `<small class="text-muted"> | Worker: ${node.worker}</small>` : ''}
                    ${node.runtime ? `<small class="text-muted"> | Runtime: ${node.runtime.toFixed(2)}s</small>` : ''}
                    ${additionalInfo}
                </span>
            </div>
        `;

        if (hasChildren) {
            nodeHtml += `<div class="task-children" data-parent-id="${node.id}">`;
            for (var i = 0; i < node.children.length; i++) {
                nodeHtml += renderCollapsibleTaskTree(node.children[i], depth + 1, false);
            }
            nodeHtml += '</div>';
        }

        return nodeHtml;
    }

    function renderProgressBar(node) {
        if (node.progress_percent > 0) {
            return `<div class="task-progress-mini"><div class="progress-fill" style="width: ${node.progress_percent}%"></div></div> (${node.progress_percent.toFixed(1)}%)`;
        }
        return '';
    }

    function renderAdditionalInfo(node) {
        var info = '';
        
        if (node.subtasks_created > 0) {
            info += `<small class="text-muted"> | ${node.subtasks_completed}/${node.subtasks_created} subtasks</small>`;
        }

        if (node.current_step && node.total_steps) {
            info += `<small class="text-muted"> | Step ${node.current_step}/${node.total_steps}</small>`;
        }

        return info;
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

    function startRealTimeUpdates() {
        hierarchyUpdateInterval = setInterval(function() {
            // Only update if hierarchy tab is active
            if ($('#hierarchy-tab').hasClass('active') || $('#hierarchy').hasClass('active show')) {
                loadHierarchyData();
            }
        }, EnhancedMonitoringCore.config.updateIntervalMs);
    }

    function stopRealTimeUpdates() {
        if (hierarchyUpdateInterval) {
            clearInterval(hierarchyUpdateInterval);
            hierarchyUpdateInterval = null;
        }
    }

    function isHierarchyComplete(taskNode) {
        if (!taskNode) return true;
        
        // Check if current task is in a final state
        var isCurrentTaskComplete = EnhancedMonitoringCore.isTaskInFinalState(taskNode.state);
        
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
        loadHierarchyData: loadHierarchyData,
        startRealTimeUpdates: startRealTimeUpdates,
        stopRealTimeUpdates: stopRealTimeUpdates,
        isHierarchyComplete: isHierarchyComplete
    };
})();