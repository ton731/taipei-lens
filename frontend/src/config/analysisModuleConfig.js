// 通用分析模組配置
// 定義每個分析模組的視覺化樣式和基本屬性

export const ANALYSIS_MODULES = {
  // 測試模組
  test: {
    id: 'test',
    name: '測試分析',
    highlightColor: '#FF6B35',      // 填充顏色（橘紅色）
    outlineColor: '#d97706',        // 邊框顏色（深橘色）
    fillOpacity: 0.6,               // 填充透明度
    outlineWidth: 2                 // 邊框寬度
  },

  // 道路綠化優先級分析
  roadGreening: {
    id: 'roadGreening',
    name: '道路綠化優先級',
    highlightColor: '#10B981',      // 綠色
    outlineColor: '#059669',        // 深綠色
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // 建築耐震補強優先級分析
  seismicStrengthening: {
    id: 'seismicStrengthening',
    name: '建築耐震補強優先級',
    highlightColor: '#EF4444',      // 紅色
    outlineColor: '#DC2626',        // 深紅色
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // 公園新闢選址潛力分析
  parkSiting: {
    id: 'parkSiting',
    name: '公園新闢選址潛力',
    highlightColor: '#8B5CF6',      // 紫色
    outlineColor: '#7C3AED',        // 深紫色
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // 都市更新急迫性分析
  urbanRenewal: {
    id: 'urbanRenewal',
    name: '都市更新急迫性',
    highlightColor: '#F59E0B',      // 琥珀色
    outlineColor: '#D97706',        // 深琥珀色
    fillOpacity: 0.6,
    outlineWidth: 2
  },

  // LLM AI 分析結果
  llm: {
    id: 'llm',
    name: 'AI 分析結果',
    highlightColor: '#FF6B35',      // 橘色
    outlineColor: '#d97706',        // 深橘色
    fillOpacity: 0.65,
    outlineWidth: 3,
    // 漸變色配置（從淺橘色到深橘色）
    gradientColors: {
      light: '#FED7AA',    // 淺橘色
      medium: '#FDBA74',   // 中橘色
      dark: '#EA580C'      // 深橘色
    }
  }
};

/**
 * 根據模組 ID 獲取配置
 * @param {string} moduleId - 模組 ID
 * @returns {Object} 模組配置對象
 */
export const getModuleConfig = (moduleId) => {
  return ANALYSIS_MODULES[moduleId] || null;
};

/**
 * 獲取所有模組 ID
 * @returns {Array<string>} 模組 ID 陣列
 */
export const getAllModuleIds = () => {
  return Object.keys(ANALYSIS_MODULES);
};
