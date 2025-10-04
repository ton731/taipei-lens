// 統一的圖層配置 - 包含顏色、範圍、圖例等所有相關設定
export const LAYER_CONFIGS = {
  building_age: {
    title: '建築屋齡',
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
    unit: '年',
    outlineColor: '#d67e4b'
  },
  population_density: {
    title: '人口密度',
    property: 'population_density',
    // 使用分位數斷點，讓顏色分布更均勻
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
    unit: '人/km²',
    outlineColor: '#d67e4b'
  },
  elderly_ratio: {
    title: '高齡比例',
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
    title: '高齡中獨居比例',
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
    title: '低收入戶比例',
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
  },
  structural_vulnerability: {
    title: '結構脆弱度',
    property: 'fragility_curve',
    colorStops: [
      { value: 0, color: '#fef2f2' },      // 極淺紅 - 低風險
      { value: 0.2, color: '#fecaca' },    // 淺紅
      { value: 0.4, color: '#fca5a5' },    // 中紅  
      { value: 0.6, color: '#f87171' },    // 紅色
      { value: 0.8, color: '#ef4444' },    // 深紅
      { value: 1, color: '#b91c1c' }       // 極深紅 - 高風險
    ],
    minValue: 0,
    maxValue: 1,
    unit: '',
    outlineColor: '#ef4444',
    isDynamic: true
  }
};

/**
 * 根據配置生成 Mapbox 的 fill-color 表達式
 * @param {Object} layerConfig - 圖層配置對象
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
 * 根據配置生成圖例的 gradient CSS
 * @param {Object} layerConfig - 圖層配置對象
 * @returns {string} CSS gradient string
 */
export const generateLegendGradient = (layerConfig) => {
  const colors = layerConfig.colorStops.map(stop => stop.color).join(', ');
  return `linear-gradient(to right, ${colors})`;
};

/**
 * 從 fragility curve 數據中插值計算特定地震強度下的倒塌機率
 * @param {Object} fragilityCurve - fragility curve 數據 {強度: 機率}
 * @param {number} targetIntensity - 目標地震強度
 * @returns {number} 倒塌機率 (0-1)
 */
export const interpolateFragilityCurve = (fragilityCurve, targetIntensity) => {
  if (!fragilityCurve || typeof fragilityCurve !== 'object') {
    return 0;
  }

  const intensities = Object.keys(fragilityCurve).map(k => parseFloat(k)).sort((a, b) => a - b);
  
  if (intensities.length === 0) {
    return 0;
  }

  // 如果目標強度小於最小值，返回最小值對應的機率
  if (targetIntensity <= intensities[0]) {
    return fragilityCurve[intensities[0]] || 0;
  }

  // 如果目標強度大於最大值，返回最大值對應的機率
  if (targetIntensity >= intensities[intensities.length - 1]) {
    return fragilityCurve[intensities[intensities.length - 1]] || 0;
  }

  // 找到目標強度的相鄰兩個點進行線性插值
  for (let i = 0; i < intensities.length - 1; i++) {
    const lowerIntensity = intensities[i];
    const upperIntensity = intensities[i + 1];
    
    if (targetIntensity >= lowerIntensity && targetIntensity <= upperIntensity) {
      const lowerProb = fragilityCurve[lowerIntensity] || 0;
      const upperProb = fragilityCurve[upperIntensity] || 0;
      
      // 線性插值
      const ratio = (targetIntensity - lowerIntensity) / (upperIntensity - lowerIntensity);
      return lowerProb + ratio * (upperProb - lowerProb);
    }
  }

  return 0;
};

/**
 * 生成結構脆弱度圖層的動態 fill-color 表達式
 * @param {number} earthquakeIntensity - 地震強度
 * @returns {Array} Mapbox expression
 */
export const generateStructuralVulnerabilityExpression = (earthquakeIntensity) => {
  const config = LAYER_CONFIGS.structural_vulnerability;
  
  // 使用 Mapbox expression 來動態計算每個建築物的倒塌機率
  const expression = [
    'case',
    ['has', 'fragility_curve'],
    [
      'interpolate',
      ['linear'],
      // 這裡需要一個自定義函數來處理 fragility curve 插值
      // 由於 Mapbox expression 的限制，我們先用簡化版本
      ['coalesce', ['get', earthquakeIntensity.toString(), ['get', 'fragility_curve']], 0],
      ...config.colorStops.flatMap(stop => [stop.value, stop.color])
    ],
    config.colorStops[0].color // 默認顏色
  ];
  
  return expression;
};
