import React from 'react';
import RadioLayerToggle from '../../ui/RadioLayerToggle';

const DataLayersModule = ({ onLayerChange, activeLegends = [], selectedLayer = null }) => {
  const layers = [
    {
      id: 'building_age',
      label: '建築屋齡',
      description: '建築物平均屋齡分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2" fill="none"/>
          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" fill="none"/>
          <line x1="12" y1="12" x2="12" y2="8" stroke="currentColor" strokeWidth="2"/>
        </svg>
      )
    },
    {
      id: 'population_density',
      label: '人口密度',
      description: '單位面積人口分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2" fill="none"/>
          <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M16 3.13a4 4 0 0 1 0 7.75" stroke="currentColor" strokeWidth="2" fill="none"/>
        </svg>
      )
    },
    {
      id: 'elderly_ratio',
      label: '高齡比例',
      description: '65歲以上人口比例分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M5.5 21v-2a7.5 7.5 0 0 1 13 0v2" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M12 11v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      )
    },
    {
      id: 'elderly_alone_ratio',
      label: '高齡中獨居比例',
      description: '高齡獨居人口比例分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M5.5 21v-2a7.5 7.5 0 0 1 13 0v2" stroke="currentColor" strokeWidth="2" fill="none"/>
          <rect x="9" y="13" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2" fill="none"/>
        </svg>
      )
    },
    {
      id: 'low_income_ratio',
      label: '低收入戶比例',
      description: '低收入戶比例分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      )
    },
    {
      id: 'structural_vulnerability',
      label: '結構脆弱度',
      description: '結構倒塌機率',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2l3.5 7h7l-5.5 4 2 7-7-5-7 5 2-7-5.5-4h7z" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M8 16l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      )
    }
  ];

  const handleLayerChange = (layerId) => {
    console.log('DataLayersModule: 圖層變化', { layerId, selectedLayer });
    // 如果點擊已選中的圖層，則取消選擇
    if (selectedLayer === layerId) {
      console.log('DataLayersModule: 取消選擇圖層', layerId);
      // 通知父組件取消選擇
      if (onLayerChange) {
        onLayerChange(null);
      }
    } else {
      console.log('DataLayersModule: 選擇新圖層', layerId);
      // 通知父組件圖層變化
      if (onLayerChange) {
        onLayerChange(layerId);
      }
    }
  };

  return (
    <div style={{
      padding: '16px',
      borderBottom: '1px solid #e5e5e5'
    }}>
      <div style={{
        fontSize: '13px',
        color: '#666',
        lineHeight: '1.4',
        marginBottom: '12px'
      }}>
        選擇一個基礎數據圖層進行視覺化探查（一次只能顯示一個圖層）
      </div>

      <div>
        {layers.map((layer) => (
          <RadioLayerToggle
            key={layer.id}
            id={layer.id}
            label={layer.label}
            description={layer.description}
            icon={layer.icon}
            checked={selectedLayer === layer.id}
            onChange={() => handleLayerChange(layer.id)}
          />
        ))}
      </div>

      {/* 圖例顯示區域 - 緊湊整合設計 */}
      {activeLegends.length > 0 && (
        <div style={{
          marginTop: '12px',
          marginLeft: '12px',
          marginRight: '12px'
        }}>
          {activeLegends.map((legend, index) => (
            <div key={index}>
              {/* 漸層色階顯示 */}
              {legend.type === 'gradient' && (
                <div>
                  <div style={{
                    height: '8px',
                    background: legend.gradient,
                    borderRadius: '3px',
                    marginBottom: '4px'
                  }}></div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '10px',
                    color: '#888'
                  }}>
                    <span>{legend.minLabel}</span>
                    <span>{legend.maxLabel}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DataLayersModule;