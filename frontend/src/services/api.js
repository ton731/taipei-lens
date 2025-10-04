// API 服務層，處理與後端的通訊

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * 獲取建築物 Mapbox tileset 資訊（不暴露 tileset ID）
 * @returns {Promise<Object>} tileset 資訊
 */
export const getBuildingTilesetInfo = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/building-tileset-info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fetch building tileset info:', error);
    throw error;
  }
};

/**
 * 建構建築物 tiles URL，指向後端代理（不暴露 tileset ID）
 * @returns {string[]} tiles URL 陣列
 */
export const getBuildingTilesUrls = () => {
  return [`${API_BASE_URL}/mapbox/building-tiles/{z}/{x}/{y}.pbf`];
};

/**
 * 取得建築物 tileset 的 Mapbox URL（用於 source.url 格式）
 * 注意：這個函式會從後端取得 tileset ID，然後組裝成 mapbox:// URL
 * @returns {Promise<string>} mapbox:// 格式的 URL
 */
export const getBuildingMapboxUrl = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/building-mapbox-url`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get building mapbox URL: ${response.status}`);
    }

    const data = await response.json();
    return data.url;  // 返回 "mapbox://tonychou.xxx" 格式的 URL
  } catch (error) {
    console.error('Failed to fetch building mapbox URL:', error);
    throw error;
  }
};

/**
 * 檢查後端健康狀態
 * @returns {Promise<Object>} 健康狀態
 */
export const checkBackendHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/health`);
    return await response.json();
  } catch (error) {
    console.error('Backend health check failed:', error);
    return { status: 'unhealthy', error: error.message };
  }
};

/**
 * 獲取行政區 Mapbox tileset 資訊（不暴露 tileset ID）
 * @returns {Promise<Object>} tileset 資訊
 */
export const getDistrictTilesetInfo = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/district-tileset-info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fetch district tileset info:', error);
    throw error;
  }
};

/**
 * 建構行政區 tiles URL，指向後端代理（不暴露 tileset ID）
 * @returns {string[]} tiles URL 陣列
 */
export const getDistrictTilesUrls = () => {
  return [`${API_BASE_URL}/mapbox/district-tiles/{z}/{x}/{y}.pbf`];
};

/**
 * 取得行政區 tileset 的 Mapbox URL（用於 source.url 格式）
 * 注意：這個函式會從後端取得 tileset ID，然後組裝成 mapbox:// URL
 * @returns {Promise<string>} mapbox:// 格式的 URL
 */
export const getDistrictMapboxUrl = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/district-mapbox-url`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get district mapbox URL: ${response.status}`);
    }

    const data = await response.json();
    return data.url;  // 返回 "mapbox://tonychou.xxx" 格式的 URL
  } catch (error) {
    console.error('Failed to fetch district mapbox URL:', error);
    throw error;
  }
};

/**
 * 獲取最小統計區域 Mapbox tileset 資訊（不暴露 tileset ID）
 * @returns {Promise<Object>} tileset 資訊
 */
export const getStatisticalAreaTilesetInfo = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/statistical-area-tileset-info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fetch statistical area tileset info:', error);
    throw error;
  }
};

/**
 * 建構最小統計區域 tiles URL，指向後端代理（不暴露 tileset ID）
 * @returns {string[]} tiles URL 陣列
 */
export const getStatisticalAreaTilesUrls = () => {
  return [`${API_BASE_URL}/mapbox/statistical-area-tiles/{z}/{x}/{y}.pbf`];
};

/**
 * 取得最小統計區域 tileset 的 Mapbox URL（用於 source.url 格式）
 * 注意：這個函式會從後端取得 tileset ID，然後組裝成 mapbox:// URL
 * @returns {Promise<string>} mapbox:// 格式的 URL
 */
export const getStatisticalAreaMapboxUrl = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/statistical-area-mapbox-url`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get statistical area mapbox URL: ${response.status}`);
    }

    const data = await response.json();
    return data.url;  // 返回 "mapbox://tonychou.xxx" 格式的 URL
  } catch (error) {
    console.error('Failed to fetch statistical area mapbox URL:', error);
    throw error;
  }
};