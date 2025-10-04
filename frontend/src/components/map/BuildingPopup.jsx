import React from 'react';
import FragilityCurve from '../charts/FragilityCurve';

/**
 * Building Popup Component
 * @param {Object} props.data - Hover information
 */
const BuildingPopup = ({ data }) => {
  const displayFields = ['height', 'floor', 'area'];
  
  // 調試：檢查建築物完整數據結構
  React.useEffect(() => {
    console.log('=== BuildingPopup 建築物數據調試 ===');
    console.log('完整 data 對象:', data);
    console.log('data.properties:', data.properties);
    
    if (data.properties) {
      console.log('所有屬性鍵值:', Object.keys(data.properties));
      console.log('屬性數量:', Object.keys(data.properties).length);
      
      // 檢查 fragility_curve
      if (data.properties.fragility_curve) {
        console.log('✅ 找到 fragility_curve 數據:', data.properties.fragility_curve);
        console.log('fragility_curve 型態:', typeof data.properties.fragility_curve);
        console.log('fragility_curve 鍵值:', Object.keys(data.properties.fragility_curve));
        console.log('fragility_curve 值:', Object.values(data.properties.fragility_curve));
      } else {
        console.log('❌ 沒有找到 fragility_curve 屬性');
        
        // 檢查是否有相似的屬性名稱
        const keys = Object.keys(data.properties);
        const similarKeys = keys.filter(key => 
          key.toLowerCase().includes('fragility') || 
          key.toLowerCase().includes('curve') ||
          key.toLowerCase().includes('vulnerability') ||
          key.toLowerCase().includes('seismic')
        );
        
        if (similarKeys.length > 0) {
          console.log('找到相似的屬性:', similarKeys);
          similarKeys.forEach(key => {
            console.log(`${key}:`, data.properties[key]);
          });
        }
      }
    } else {
      console.log('❌ data.properties 不存在');
    }
    console.log('=== BuildingPopup 調試結束 ===');
  }, [data]);

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
      {displayFields.map(field => {
        const value = data.properties?.[field];
        let displayValue = value?.toString() || 'null';

        // Add units to values
        if (value && value !== 'null') {
          if (field === 'height') {
            displayValue = `${value} m`;
          } else if (field === 'area') {
            displayValue = `${value} m²`;
          }
        }

        return (
          <div key={field} style={{
            marginBottom: '2px',
            fontSize: '12px'
          }}>
            <span style={{ color: '#6c757d', fontWeight: '500' }}>{field}:</span>{' '}
            <span style={{ color: value ? '#212529' : '#999999' }}>
              {displayValue}
            </span>
          </div>
        );
      })}

      {/* Divider */}
      <div style={{
        height: '1px',
        backgroundColor: '#dee2e6',
        margin: '8px -12px 8px -12px'
      }}></div>

      {/* Fragility Curve Title */}
      <div style={{
        fontSize: '12px',
        fontWeight: '600',
        color: '#495057',
        marginBottom: '6px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px'
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ color: '#ef4444' }}>
          <path d="M2 12h3l2-8 4 16 4-12 2 4h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Seismic Fragility Curve
      </div>

      {/* Fragility Curve Chart */}
      <FragilityCurve fragilityCurveData={data.properties?.fragility_curve} />
    </div>
  );
};

export default BuildingPopup;
