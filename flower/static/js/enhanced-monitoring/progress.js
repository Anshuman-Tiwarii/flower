/**
 * Enhanced Task Monitoring - Progress Module
 * Handles real-time progress tracking and subtask summaries
 */

var ProgressMonitoring = (function () {
    "use strict";

    var isInitialized = false;
    var progressUpdateInterval;

    function init() {
        if (isInitialized) return;
        
        // Initialize progress tab
        initializeProgressTab();
        
        // Listen for tab activation events
        $(document).on('enhanced-monitoring:tab-shown', function(e, data) {
            if (data.tab === '#progress') {
                loadProgressData();
            }
        });
        
        isInitialized = true;
        console.log('Progress monitoring module initialized');
    }

    function initializeProgressTab() {
        loadProgressData();
    }

    function loadProgressData() {
        EnhancedMonitoringCore.showLoadingMessage('#progress-container', 'Loading progress data...');
        
        EnhancedMonitoringCore.makeApiRequest('progress', {
            success: function(data) {
                renderProgressDisplay(data);
            },
            error: function(xhr, status, error) {
                console.log('Error loading progress data:', error);
                EnhancedMonitoringCore.showErrorMessage('#progress-container', 'Unable to load progress data');
            }
        });
    }

    function renderProgressDisplay(data) {
        var container = $('#progress-container');
        container.empty();

        if (!data.has_custom_progress) {
            EnhancedMonitoringCore.showNoDataMessage('#progress-container', 'No custom progress data available for this task');
            return;
        }

        // Stop polling if task is completed
        var taskState = data.task_info && data.task_info.state;
        if (taskState && EnhancedMonitoringCore.isTaskInFinalState(taskState)) {
            stopRealTimeUpdates();
        }

        var progress = data.current_progress;
        var progressHtml = '';

        // Main progress bar
        if (progress.progress_percent !== undefined) {
            progressHtml += renderMainProgressBar(progress);
        }

        // Chain progress (for sequential tasks)
        if (progress.current_step && progress.total_steps) {
            progressHtml += renderChainProgress(progress);
        }

        // Stage progress (for tasks with stages)
        if (progress.stage_progress !== undefined && progress.stage_progress > 0) {
            progressHtml += renderStageProgress(progress);
        }

        container.html(progressHtml);

        // Render subtask summary
        renderSubtaskSummary(progress);
        
        // Update failure analysis tab badge if there are failed subtasks
        updateFailureTabBadge(progress);
    }

    function renderMainProgressBar(progress) {
        return `
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

    function renderChainProgress(progress) {
        return `
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

    function renderStageProgress(progress) {
        return `
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

    function startRealTimeUpdates() {
        // Clear any existing interval
        stopRealTimeUpdates();
        
        progressUpdateInterval = setInterval(function() {
            // Only update if progress tab is active
            if ($('#progress-tab').hasClass('active') || $('#progress').hasClass('active show')) {
                loadProgressData();
            }
        }, EnhancedMonitoringCore.config.updateIntervalMs);
        
        EnhancedMonitoringCore.setUpdateInterval(progressUpdateInterval);
    }

    function stopRealTimeUpdates() {
        if (progressUpdateInterval) {
            clearInterval(progressUpdateInterval);
            progressUpdateInterval = null;
        }
    }

    function isProgressComplete(progressData) {
        if (!progressData || !progressData.task_info) return false;
        return EnhancedMonitoringCore.isTaskInFinalState(progressData.task_info.state);
    }

    // Public API
    return {
        init: init,
        loadProgressData: loadProgressData,
        startRealTimeUpdates: startRealTimeUpdates,
        stopRealTimeUpdates: stopRealTimeUpdates,
        isProgressComplete: isProgressComplete
    };
})();