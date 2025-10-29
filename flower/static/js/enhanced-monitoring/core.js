/**
 * Enhanced Task Monitoring - Core Utilities
 * Shared utilities and base functionality for all monitoring modules
 */

var EnhancedMonitoringCore = (function () {
    "use strict";

    var taskId;
    var updateInterval;
    var config = {
        updateIntervalMs: 3000,
        maxRetries: 3,
        retryDelayMs: 1000
    };

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
            return false;
        }
        
        console.log('Enhanced monitoring initialized for task:', taskId);
        return true;
    }

    function getTaskId() {
        return taskId;
    }

    function setUpdateInterval(interval) {
        updateInterval = interval;
    }

    function getUpdateInterval() {
        return updateInterval;
    }

    function clearUpdateInterval() {
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
    }

    function makeApiRequest(endpoint, options) {
        options = options || {};
        var defaults = {
            method: 'GET',
            timeout: 10000,
            retries: config.maxRetries
        };
        
        var settings = $.extend({}, defaults, options);
        
        return $.ajax({
            url: url_prefix() + '/api/task/' + taskId + '/' + endpoint,
            method: settings.method,
            timeout: settings.timeout,
            success: settings.success,
            error: settings.error
        });
    }

    function showErrorMessage(container, message) {
        var errorHtml = '<div class="alert alert-warning">' + message + '</div>';
        $(container).html(errorHtml);
    }

    function showLoadingMessage(container, message) {
        message = message || 'Loading...';
        var loadingHtml = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin"></i> ' + message + '</div>';
        $(container).html(loadingHtml);
    }

    function showNoDataMessage(container, message) {
        message = message || 'No data available';
        var noDataHtml = '<div class="alert alert-info">' + message + '</div>';
        $(container).html(noDataHtml);
    }

    function checkEnhancedMonitoringStatus(callback) {
        // Instead of relying on metadata, try to load actual data for each tab
        // This ensures we don't show "No data available" prematurely
        var hasAnyData = false;
        var checksCompleted = 0;
        var totalChecks = 3; // progress, hierarchy, failure-analysis
        
        function checkComplete() {
            checksCompleted++;
            if (checksCompleted === totalChecks) {
                if (hasAnyData) {
                    $('#enhanced-monitoring-badge').removeClass('d-none');
                    console.log('Enhanced monitoring data found');
                    if (callback) callback(true);
                } else {
                    console.log('No enhanced monitoring data available for task:', taskId);
                    if (callback) callback(false);
                }
            }
        }
        
        // Check for progress data
        makeApiRequest('progress', {
            success: function(data) {
                if (data && data.has_progress) {
                    hasAnyData = true;
                }
                checkComplete();
            },
            error: function() {
                checkComplete();
            }
        });
        
        // Check for hierarchy data
        makeApiRequest('hierarchy', {
            success: function(data) {
                if (data && data.has_hierarchy) {
                    hasAnyData = true;
                }
                checkComplete();
            },
            error: function() {
                checkComplete();
            }
        });
        
        // Check for failure analysis data
        makeApiRequest('failure-analysis', {
            success: function(data) {
                if (data && data.has_failure_analysis) {
                    hasAnyData = true;
                }
                checkComplete();
            },
            error: function() {
                checkComplete();
            }
        });
    }


    function setupTabHandlers() {
        // Handle tab switching
        $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
            var target = $(e.target).attr("href");
            
            // Notify modules about tab activation
            $(document).trigger('enhanced-monitoring:tab-shown', {
                tab: target,
                taskId: taskId
            });
        });
    }

    function isTaskInFinalState(taskState) {
        var finalStates = ['SUCCESS', 'FAILURE', 'REVOKED'];
        return finalStates.includes(taskState);
    }

    function navigateToTask(targetTaskId) {
        if (targetTaskId && targetTaskId !== taskId) {
            window.location.href = url_prefix() + '/task/' + encodeURIComponent(targetTaskId);
        }
    }

    function formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown';
        
        if (typeof moment !== 'undefined') {
            return moment.unix(timestamp).format('YYYY-MM-DD HH:mm:ss');
        } else {
            return new Date(timestamp * 1000).toLocaleString();
        }
    }

    function getStateBadgeClass(state) {
        var classes = {
            'SUCCESS': 'success',
            'FAILURE': 'danger',
            'PENDING': 'secondary',
            'STARTED': 'primary',
            'RETRY': 'warning',
            'REVOKED': 'dark',
            'RECEIVED': 'info'
        };
        return classes[state] || 'secondary';
    }

    function truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    function debounce(func, wait) {
        var timeout;
        return function executedFunction() {
            var context = this;
            var args = arguments;
            var later = function() {
                timeout = null;
                func.apply(context, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Public API
    return {
        init: init,
        getTaskId: getTaskId,
        url_prefix: url_prefix,
        makeApiRequest: makeApiRequest,
        showErrorMessage: showErrorMessage,
        showLoadingMessage: showLoadingMessage,
        showNoDataMessage: showNoDataMessage,
        checkEnhancedMonitoringStatus: checkEnhancedMonitoringStatus,
        setupTabHandlers: setupTabHandlers,
        setUpdateInterval: setUpdateInterval,
        getUpdateInterval: getUpdateInterval,
        clearUpdateInterval: clearUpdateInterval,
        isTaskInFinalState: isTaskInFinalState,
        navigateToTask: navigateToTask,
        formatTimestamp: formatTimestamp,
        getStateBadgeClass: getStateBadgeClass,
        truncateText: truncateText,
        debounce: debounce,
        config: config
    };
})();