/**
 * Enhanced Task Monitoring - Main Orchestrator
 * Coordinates all monitoring modules and provides unified interface
 */

var EnhancedTaskMonitoring = (function () {
    "use strict";

    var isInitialized = false;
    var activeModules = [];

    function init() {
        if (isInitialized) {
            console.log('Enhanced monitoring already initialized');
            return;
        }

        console.log('Initializing Enhanced Task Monitoring...');

        // Initialize core utilities first
        if (!EnhancedMonitoringCore.init()) {
            console.log('Failed to initialize core utilities');
            return;
        }

        // Initialize all monitoring modules
        initializeModules();

        // Check if task has enhanced monitoring data
        EnhancedMonitoringCore.checkEnhancedMonitoringStatus(function(hasEnhancedData) {
            if (hasEnhancedData) {
                // Start real-time updates
                startRealTimeUpdates();
                
                // Setup global tab handlers
                EnhancedMonitoringCore.setupTabHandlers();
                
                console.log('Enhanced monitoring fully initialized with real-time updates');
            } else {
                console.log('Task does not have enhanced monitoring data');
            }
        });

        // Setup cleanup on page unload
        setupCleanupHandlers();

        isInitialized = true;
    }

    function initializeModules() {
        try {
            // Initialize Progress Monitoring
            if (typeof ProgressMonitoring !== 'undefined') {
                ProgressMonitoring.init();
                activeModules.push('progress');
                console.log('Progress monitoring module loaded');
            }

            // Initialize Hierarchy Monitoring
            if (typeof HierarchyMonitoring !== 'undefined') {
                HierarchyMonitoring.init();
                activeModules.push('hierarchy');
                console.log('Hierarchy monitoring module loaded');
            }

            // Initialize Failure Analysis
            if (typeof FailureAnalysis !== 'undefined') {
                FailureAnalysis.init();
                activeModules.push('failure-analysis');
                console.log('Failure analysis module loaded');
            }

            console.log('Active modules:', activeModules);
        } catch (error) {
            console.error('Error initializing monitoring modules:', error);
        }
    }

    function startRealTimeUpdates() {
        // Start real-time updates for all modules
        if (activeModules.includes('progress') && ProgressMonitoring.startRealTimeUpdates) {
            ProgressMonitoring.startRealTimeUpdates();
        }

        if (activeModules.includes('hierarchy') && HierarchyMonitoring.startRealTimeUpdates) {
            HierarchyMonitoring.startRealTimeUpdates();
        }

        console.log('Real-time updates started for active modules');
    }

    function stopRealTimeUpdates() {
        // Stop real-time updates for all modules
        if (activeModules.includes('progress') && ProgressMonitoring.stopRealTimeUpdates) {
            ProgressMonitoring.stopRealTimeUpdates();
        }

        if (activeModules.includes('hierarchy') && HierarchyMonitoring.stopRealTimeUpdates) {
            HierarchyMonitoring.stopRealTimeUpdates();
        }

        // Clear core interval
        EnhancedMonitoringCore.clearUpdateInterval();

        console.log('Real-time updates stopped for all modules');
    }

    function setupCleanupHandlers() {
        // Cleanup when leaving the page
        $(window).on('beforeunload', function() {
            stopRealTimeUpdates();
        });

        // Cleanup when page becomes hidden (browser tab switching)
        if (typeof document.hidden !== 'undefined') {
            document.addEventListener('visibilitychange', function() {
                if (document.hidden) {
                    stopRealTimeUpdates();
                } else if (isInitialized) {
                    startRealTimeUpdates();
                }
            });
        }
    }

    function refreshAllData() {
        console.log('Refreshing all monitoring data...');
        
        if (activeModules.includes('progress') && ProgressMonitoring.loadProgressData) {
            ProgressMonitoring.loadProgressData();
        }

        if (activeModules.includes('hierarchy') && HierarchyMonitoring.loadHierarchyData) {
            HierarchyMonitoring.loadHierarchyData();
        }

        if (activeModules.includes('failure-analysis') && FailureAnalysis.loadFailureAnalysis) {
            FailureAnalysis.loadFailureAnalysis();
        }
    }

    function getActiveModules() {
        return activeModules.slice(); // Return a copy
    }

    function getTaskId() {
        return EnhancedMonitoringCore.getTaskId();
    }

    function navigateToTask(taskId) {
        return EnhancedMonitoringCore.navigateToTask(taskId);
    }

    // Public API - maintains backward compatibility with existing code
    return {
        init: init,
        loadProgressData: function() {
            if (activeModules.includes('progress') && ProgressMonitoring.loadProgressData) {
                return ProgressMonitoring.loadProgressData();
            }
        },
        loadHierarchyData: function() {
            if (activeModules.includes('hierarchy') && HierarchyMonitoring.loadHierarchyData) {
                return HierarchyMonitoring.loadHierarchyData();
            }
        },
        loadFailureAnalysis: function() {
            if (activeModules.includes('failure-analysis') && FailureAnalysis.loadFailureAnalysis) {
                return FailureAnalysis.loadFailureAnalysis();
            }
        },
        stopRealTimeUpdates: stopRealTimeUpdates,
        startRealTimeUpdates: startRealTimeUpdates,
        refreshAllData: refreshAllData,
        navigateToTask: navigateToTask,
        getActiveModules: getActiveModules,
        getTaskId: getTaskId,
        
        // Module access (for advanced usage)
        modules: {
            core: function() { return typeof EnhancedMonitoringCore !== 'undefined' ? EnhancedMonitoringCore : null; },
            progress: function() { return typeof ProgressMonitoring !== 'undefined' ? ProgressMonitoring : null; },
            hierarchy: function() { return typeof HierarchyMonitoring !== 'undefined' ? HierarchyMonitoring : null; },
            failureAnalysis: function() { return typeof FailureAnalysis !== 'undefined' ? FailureAnalysis : null; }
        }
    };
})();

// Initialize when document is ready
$(document).ready(function () {
    // Only initialize on task detail pages
    if (window.location.pathname.includes('/task/')) {
        // Small delay to ensure all modules are loaded
        setTimeout(function() {
            EnhancedTaskMonitoring.init();
        }, 100);
    }
});