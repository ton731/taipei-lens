// API service layer for handling backend communication

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Fetch building Mapbox tileset information (without exposing tileset ID)
 * @returns {Promise<Object>} tileset information
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
    throw error;
  }
};

/**
 * Construct building tiles URL pointing to backend proxy (without exposing tileset ID)
 * @returns {string[]} Array of tiles URLs
 */
export const getBuildingTilesUrls = () => {
  return [`${API_BASE_URL}/mapbox/building-tiles/{z}/{x}/{y}.pbf`];
};

/**
 * Get building tileset Mapbox URL (for source.url format)
 * Note: This function retrieves tileset ID from backend and assembles it into a mapbox:// URL
 * @returns {Promise<string>} mapbox:// format URL
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
    return data.url;  // Returns URL in "mapbox://tonychou.xxx" format
  } catch (error) {
    throw error;
  }
};

/**
 * Check backend health status
 * @returns {Promise<Object>} Health status
 */
export const checkBackendHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mapbox/health`);
    return await response.json();
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
};

/**
 * Fetch district Mapbox tileset information (without exposing tileset ID)
 * @returns {Promise<Object>} tileset information
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
    throw error;
  }
};

/**
 * Construct district tiles URL pointing to backend proxy (without exposing tileset ID)
 * @returns {string[]} Array of tiles URLs
 */
export const getDistrictTilesUrls = () => {
  return [`${API_BASE_URL}/mapbox/district-tiles/{z}/{x}/{y}.pbf`];
};

/**
 * Get district tileset Mapbox URL (for source.url format)
 * Note: This function retrieves tileset ID from backend and assembles it into a mapbox:// URL
 * @returns {Promise<string>} mapbox:// format URL
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
    return data.url;  // Returns URL in "mapbox://tonychou.xxx" format
  } catch (error) {
    throw error;
  }
};

/**
 * Fetch statistical area Mapbox tileset information (without exposing tileset ID)
 * @returns {Promise<Object>} tileset information
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
    throw error;
  }
};

/**
 * Construct statistical area tiles URL pointing to backend proxy (without exposing tileset ID)
 * @returns {string[]} Array of tiles URLs
 */
export const getStatisticalAreaTilesUrls = () => {
  return [`${API_BASE_URL}/mapbox/statistical-area-tiles/{z}/{x}/{y}.pbf`];
};

/**
 * Get statistical area tileset Mapbox URL (for source.url format)
 * Note: This function retrieves tileset ID from backend and assembles it into a mapbox:// URL
 * @returns {Promise<string>} mapbox:// format URL
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
    return data.url;  // Returns URL in "mapbox://tonychou.xxx" format
  } catch (error) {
    throw error;
  }
};