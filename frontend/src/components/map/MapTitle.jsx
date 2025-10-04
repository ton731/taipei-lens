import React from 'react';

/**
 * 地圖標題組件
 */
const MapTitle = () => {
  return (
    <div style={{
      position: 'absolute',
      top: '20px',
      left: '20px',
      background: 'rgba(255, 255, 255, 0.85)',
      color: '#333',
      padding: '14px 22px',
      borderRadius: '12px',
      fontSize: '18px',
      fontWeight: '600',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255, 255, 255, 0.2)'
    }}>
      Taipei Lens - 台北都市韌性規劃平台
    </div>
  );
};

export default MapTitle;
