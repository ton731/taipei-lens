// General analysis module configuration
// Defines visualization styles and basic properties for each analysis module

export const ANALYSIS_MODULES = {
  // Test module
  test: {
    id: 'test',
    name: 'Test Analysis',
    highlightColor: '#FF6B35',      // Fill color (orange-red)
    outlineColor: '#d97706',        // Outline color (dark orange)
    fillOpacity: 0.6,               // Fill opacity
    outlineWidth: 2                 // Outline width
  },

  // Road greening priority analysis
  roadGreening: {
    id: 'roadGreening',
    name: 'Road Greening Priority',
    highlightColor: '#FF6B35',      // Orange
    outlineColor: '#d97706',        // Dark orange
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // Building Building Seismic Retrofit Urgency Assessment
  seismicStrengthening: {
    id: 'seismicStrengthening',
    name: 'Seismic Strengthening Priority',
    highlightColor: '#FF6B35',      // Orange
    outlineColor: '#d97706',        // Dark orange
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // Park Site Suitability Analysis
  parkSiting: {
    id: 'parkSiting',
    name: 'Park Siting Potential',
    highlightColor: '#FF6B35',      // Orange
    outlineColor: '#d97706',        // Dark orange
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // Urban Renewal Priority Assessment
  urbanRenewal: {
    id: 'urbanRenewal',
    name: 'Urban Renewal Urgency',
    highlightColor: '#FF6B35',      // Orange
    outlineColor: '#d97706',        // Dark orange
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // LLM AI analysis result
  llm: {
    id: 'llm',
    name: 'AI Analysis Result',
    highlightColor: '#FF6B35',      // Orange
    outlineColor: '#d97706',        // Dark orange
    fillOpacity: 0.65,
    outlineWidth: 3,
    // Gradient color configuration (light to dark orange)
    gradientColors: {
      light: '#FED7AA',    // Light orange
      medium: '#FDBA74',   // Medium orange
      dark: '#EA580C'      // Dark orange
    }
  }
};

/**
 * Get configuration by module ID
 * @param {string} moduleId - Module ID
 * @returns {Object} Module configuration object
 */
export const getModuleConfig = (moduleId) => {
  return ANALYSIS_MODULES[moduleId] || null;
};

/**
 * Get all module IDs
 * @returns {Array<string>} Array of module IDs
 */
export const getAllModuleIds = () => {
  return Object.keys(ANALYSIS_MODULES);
};
