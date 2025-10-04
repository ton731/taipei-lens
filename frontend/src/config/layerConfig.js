// Unified layer configuration - Contains all related settings such as colors, ranges, legends, etc.
export const LAYER_CONFIGS = {
  building_age: {
    title: 'Building Age',
    property: 'avg_building_age',
    colorStops: [
      { value: 0, color: '#fff7e6' },
      { value: 14, color: '#fdd49e' },
      { value: 28, color: '#fdae6b' },
      { value: 42, color: '#fd8d3c' },
      { value: 56, color: '#e6550d' },
      { value: 70, color: '#8c3a00' }
    ],
    minValue: 0,
    maxValue: 70,
    unit: 'years',
    outlineColor: '#d67e4b'
  },
  population_density: {
    title: 'Population Density',
    property: 'population_density',
    // Using quantile breakpoints for more even color distribution
    colorStops: [
      { value: 0, color: '#fff5eb' },       // 0th percentile
      { value: 16445, color: '#fee6ce' },   // 20th percentile
      { value: 37109, color: '#fdbb84' },   // 40th percentile
      { value: 52083, color: '#fc8d59' },   // 60th percentile
      { value: 69423, color: '#e34a33' },   // 80th percentile
      { value: 447953, color: '#b30000' }   // 100th percentile (max)
    ],
    minValue: 0,
    maxValue: 447953,
    unit: 'people/km²',
    outlineColor: '#d67e4b'
  },
  elderly_ratio: {
    title: 'Elderly Ratio',
    property: 'pop_elderly_percentage',
    colorStops: [
      { value: 19.38, color: '#fff0e6' },
      { value: 20.57, color: '#ffe4cc' },
      { value: 21.76, color: '#ffc299' },
      { value: 22.95, color: '#ff9966' },
      { value: 24.14, color: '#ff6633' },
      { value: 25.32, color: '#cc4400' }
    ],
    minValue: 19.38,
    maxValue: 25.32,
    unit: '%',
    outlineColor: '#d67e4b'
  },
  elderly_alone_ratio: {
    title: 'Elderly Living Alone Ratio',
    property: 'elderly_alone_percentage',
    colorStops: [
      { value: 0.9, color: '#fffaf0' },
      { value: 1.57, color: '#ffe5cc' },
      { value: 2.24, color: '#ffcc99' },
      { value: 2.91, color: '#ff9966' },
      { value: 3.58, color: '#ff6633' },
      { value: 4.27, color: '#b34700' }
    ],
    minValue: 0.9,
    maxValue: 4.27,
    unit: '%',
    outlineColor: '#d67e4b'
  },
  low_income_ratio: {
    title: 'Low Income Ratio',
    property: 'low_income_percentage',
    colorStops: [
      { value: 0.36, color: '#fef8f0' },
      { value: 0.71, color: '#fee0cc' },
      { value: 1.06, color: '#fdb683' },
      { value: 1.41, color: '#f37c4c' },
      { value: 1.76, color: '#d9441d' },
      { value: 2.11, color: '#8b2800' }
    ],
    minValue: 0.36,
    maxValue: 2.11,
    unit: '%',
    outlineColor: '#d67e4b'
  }
};

/**
 * Generate Mapbox fill-color expression based on configuration
 * @param {Object} layerConfig - Layer configuration object
 * @returns {Array} Mapbox expression
 */
export const generateFillColorExpression = (layerConfig) => {
  const expression = ['interpolate', ['linear'], ['get', layerConfig.property]];
  layerConfig.colorStops.forEach(stop => {
    expression.push(stop.value, stop.color);
  });
  return expression;
};

/**
 * Generate legend gradient CSS based on configuration
 * @param {Object} layerConfig - Layer configuration object
 * @returns {string} CSS gradient string
 */
export const generateLegendGradient = (layerConfig) => {
  const colors = layerConfig.colorStops.map(stop => stop.color).join(', ');
  return `linear-gradient(to right, ${colors})`;
};
