/**
 * Enhanced Task Monitoring - Failure Analysis Module
 * Handles comprehensive failure analysis and error reporting
 */

var FailureAnalysis = (function () {
    "use strict";

    var isInitialized = false;

    function init() {
        if (isInitialized) return;
        
        // Initialize failure analysis tab (load on first view)
        initializeFailureAnalysisTab();
        
        // Listen for tab activation events
        $(document).on('enhanced-monitoring:tab-shown', function(e, data) {
            if (data.tab === '#failure-analysis') {
                loadFailureAnalysis();
            }
        });
        
        isInitialized = true;
        console.log('Failure analysis module initialized');
    }

    function initializeFailureAnalysisTab() {
        $('#failure-tab').one('shown.bs.tab', function() {
            loadFailureAnalysis();
        });
    }

    function loadFailureAnalysis() {
        EnhancedMonitoringCore.showLoadingMessage('#failure-analysis-container', 'Loading failure analysis...');
        
        EnhancedMonitoringCore.makeApiRequest('failure-analysis', {
            success: function(data) {
                renderFailureAnalysis(data);
            },
            error: function(xhr, status, error) {
                console.log('Error loading failure analysis:', error);
                EnhancedMonitoringCore.showErrorMessage('#failure-analysis-container', 'Unable to load failure analysis');
            }
        });
    }

    function renderFailureAnalysis(data) {
        var container = $('#failure-analysis-container');
        
        if (!data.has_failed && !data.has_custom_failure_data && (!data.failed_subtasks || data.failed_subtasks.length === 0)) {
            container.html('<div class="alert alert-success"><i class="fas fa-check-circle"></i> Task and all subtasks completed successfully</div>');
            return;
        }

        var failureHtml = '';

        // Render main task failure if it exists
        if (data.has_failed) {
            failureHtml += renderMainTaskFailure(data);
        }

        // Render failed subtasks section
        if (data.failed_subtasks && data.failed_subtasks.length > 0) {
            failureHtml += renderFailedSubtasksSection(data);
        }

        container.html(failureHtml);
        
        // Setup event handlers for expandable subtask details
        setupSubtaskFailureHandlers();
    }

    function renderMainTaskFailure(data) {
        return `
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
                                ${renderMainTaskErrorDetails(data)}
                            </div>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    function renderMainTaskErrorDetails(data) {
        var detailsHtml = '';
        
        if (data.custom_failure_metadata && Object.keys(data.custom_failure_metadata).length > 0) {
            detailsHtml += `
                <div class="mb-3">
                    <h6 class="text-primary">Custom Metadata</h6>
                    <div class="json-viewer">
                        <pre class="bg-white border rounded p-2">${JSON.stringify(data.custom_failure_metadata, null, 2)}</pre>
                    </div>
                </div>
            `;
        }
        
        if (data.traceback) {
            detailsHtml += `
                <div class="mt-3">
                    <h6 class="text-primary">Full Traceback</h6>
                    <pre class="bg-dark text-light p-3 rounded failure-traceback">${data.traceback}</pre>
                </div>
            `;
        }
        
        return detailsHtml;
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
        var timeStr = EnhancedMonitoringCore.formatTimestamp(subtask.failed_at || subtask.timestamp);
        var errorPreview = EnhancedMonitoringCore.truncateText(
            subtask.exception || subtask.failure_reason || 'Unknown error', 
            100
        );

        return `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <span class="expand-icon-subtask" id="expand-icon-${index}" style="cursor: pointer;" onclick="toggleSubtaskErrorDetails(${index})">▶</span>
                            <span class="text-dark" style="cursor: pointer;" onclick="toggleSubtaskErrorDetails(${index})">
                                ${subtask.task_name}
                            </span>
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
                                <i class="fas fa-clock"></i> ${timeStr}
                                ${subtask.worker ? `<span class="ms-2"><i class="fas fa-server"></i> ${subtask.worker}</span>` : ''}
                                ${subtask.failure_stage ? `<span class="ms-2"><i class="fas fa-layer-group"></i> Stage: ${subtask.failure_stage}</span>` : ''}
                            </small>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">ID: ${subtask.task_id}</small>
                        </div>
                    </div>
                    <div>
                        <a href="${EnhancedMonitoringCore.url_prefix()}/task/${subtask.task_id}" 
                           class="btn btn-outline-success btn-sm" 
                           onclick="event.stopPropagation();"
                           target="_blank">
                            <i class="fas fa-external-link-alt"></i> View Task
                        </a>
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
                        <pre class="bg-white border rounded p-2">${JSON.stringify(customMetadata, null, 2)}</pre>
                    </div>
                </div>
            `;
        }

        // Add system metrics if available
        var systemMetrics = errorDetails.system_metrics;
        if (systemMetrics) {
            detailsHtml += renderSystemMetrics(systemMetrics);
        }

        // Add full traceback if available
        if (errorDetails.full_traceback && errorDetails.full_traceback.trim() !== '') {
            detailsHtml += `
                <div class="mt-3">
                    <h6 class="text-primary">Full Traceback</h6>
                    <pre class="bg-dark text-light p-3 rounded failure-traceback">${errorDetails.full_traceback}</pre>
                </div>
            `;
        }

        return detailsHtml;
    }

    function renderSystemMetrics(systemMetrics) {
        return `
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

    function setupSubtaskFailureHandlers() {
        // Event handlers are set up via onclick attributes for simplicity
    }

    // Global function for toggling subtask error details
    window.toggleSubtaskErrorDetails = function(index) {
        var detailsElement = $('#subtask-details-' + index);
        var expandIcon = $('#expand-icon-' + index);
        
        if (detailsElement.hasClass('show')) {
            detailsElement.collapse('hide');
            expandIcon.html('▶');
        } else {
            detailsElement.collapse('show');
            expandIcon.html('▼');
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

    // Public API
    return {
        init: init,
        loadFailureAnalysis: loadFailureAnalysis
    };
})();