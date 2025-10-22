/**
 * Enhanced Task Monitoring - Compatibility Layer
 * 
 * This file maintains backward compatibility with the original monolithic implementation
 * while delegating functionality to the new modular architecture.
 * 
 * DEPRECATED: This file is kept for backward compatibility only.
 * Use the modular files in enhanced-monitoring/ directory for new development.
 */

console.warn('enhanced-monitoring.js is deprecated. Using modular implementation from enhanced-monitoring/ directory.');

// Backward compatibility aliases
if (typeof EnhancedTaskMonitoring !== 'undefined') {
    // Export the same interface for any existing code that might depend on it
    var LegacyEnhancedTaskMonitoring = EnhancedTaskMonitoring;
    
    // Log that we're using the new modular system
    console.log('Enhanced monitoring is now modular. All functionality preserved.');
} else {
    console.error('Enhanced monitoring modules not loaded properly. Check that all module files are included.');
}