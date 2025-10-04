import React from 'react';

/**
 * 統計區 Popup 組件
 * @param {Object} props.data - Hover 資訊
 */
const DistrictPopup = ({ data }) => {
  return (
    <div style={{
      padding: '10px 12px',
      fontSize: '13px',
      backgroundColor: '#f8f9fa',
      border: '1px solid #dee2e6',
      borderRadius: '6px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      fontFamily: 'system-ui, sans-serif',
      minWidth: '220px'
    }}>
      <div style={{
        fontSize: '13px',
        fontWeight: '600',
        color: '#495057',
        marginBottom: '8px',
        paddingBottom: '6px',
        borderBottom: '1px solid #dee2e6'
      }}>
        統計區資訊
      </div>
      {Object.entries(data.feature.properties).map(([key, value]) => (
        <div key={key} style={{
          marginBottom: '2px',
          fontSize: '12px'
        }}>
          <span style={{ color: '#6c757d', fontWeight: '500' }}>
            {key}:
          </span>{' '}
          <span style={{ color: '#212529' }}>
            {value}
          </span>
        </div>
      ))}
    </div>
  );
};

export default DistrictPopup;
