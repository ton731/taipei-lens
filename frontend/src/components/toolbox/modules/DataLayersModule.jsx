import React from 'react';
import RadioLayerToggle from '../../ui/RadioLayerToggle';
import StructuralVulnerabilityControl from '../../ui/StructuralVulnerabilityControl';
import { LAYER_CONFIGS, generateLegendGradient } from '../../../config/layerConfig';

const DataLayersModule = ({ onLayerChange, activeLegends = [], selectedLayer = null, earthquakeIntensity, onEarthquakeIntensityChange }) => {
  // 將結構脆弱度圖層分開，方便單獨處理
  const structuralVulnerabilityLayer = {
    id: 'structural_vulnerability',
    label: '結構脆弱度',
    description: '結構倒塌機率',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M12 2l3.5 7h7l-5.5 4 2 7-7-5-7 5 2-7-5.5-4h7z" stroke="currentColor" strokeWidth="2" fill="none"/>
        <path d="M8 16l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    )
  };

  const otherLayers = [
    {
      id: 'building_age',
      label: 'Building Age',
      description: 'Average building age distribution',
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
      label: 'Population Density',
      description: 'Population distribution per unit area',
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
      label: 'Elderly Ratio',
      description: 'Distribution of population aged 65 and above',
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
      label: 'Elderly Living Alone Ratio',
      description: 'Distribution of elderly living alone',
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
      label: 'Low Income Ratio',
      description: 'Distribution of low-income households',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      )
    },
    {
      id: 'lst',
      label: 'LST地表溫度',
      description: '地表溫度分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2" fill="none"/>
          <line x1="12" y1="1" x2="12" y2="3" stroke="currentColor" strokeWidth="2"/>
          <line x1="12" y1="21" x2="12" y2="23" stroke="currentColor" strokeWidth="2"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="currentColor" strokeWidth="2"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="currentColor" strokeWidth="2"/>
          <line x1="1" y1="12" x2="3" y2="12" stroke="currentColor" strokeWidth="2"/>
          <line x1="21" y1="12" x2="23" y2="12" stroke="currentColor" strokeWidth="2"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="currentColor" strokeWidth="2"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="currentColor" strokeWidth="2"/>
        </svg>
      )
    },
    {
      id: 'ndvi',
      label: 'NDVI植被指數',
      description: '植被覆蓋指數分布',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="currentColor" strokeWidth="2" fill="none"/>
          <polyline points="7.5,12 12,15 16.5,12" stroke="currentColor" strokeWidth="2" fill="none"/>
          <line x1="12" y1="15" x2="12" y2="21" stroke="currentColor" strokeWidth="2"/>
        </svg>
      )
    }
  ];

  const handleLayerChange = (layerId) => {
    // If clicking an already selected layer, deselect it
    if (selectedLayer === layerId) {
      // Notify parent component to deselect
      if (onLayerChange) {
        onLayerChange(null);
      }
    } else {
      // Notify parent component of layer change
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
        Select a base data layer for visual exploration.
      </div>

      <div>
        {/* 結構脆弱度圖層 - 放在最前面 */}
        <RadioLayerToggle
          key={structuralVulnerabilityLayer.id}
          id={structuralVulnerabilityLayer.id}
          label={structuralVulnerabilityLayer.label}
          description={structuralVulnerabilityLayer.description}
          icon={structuralVulnerabilityLayer.icon}
          checked={selectedLayer === structuralVulnerabilityLayer.id}
          onChange={() => handleLayerChange(structuralVulnerabilityLayer.id)}
        />

        {/* 地震強度控制 - 緊接在結構脆弱度後面 */}
        {selectedLayer === 'structural_vulnerability' && earthquakeIntensity && onEarthquakeIntensityChange && (
          <div style={{ marginTop: '8px', marginBottom: '8px' }}>
            <StructuralVulnerabilityControl
              earthquakeIntensity={earthquakeIntensity}
              onIntensityChange={onEarthquakeIntensityChange}
            />
          </div>
        )}

        {/* 結構脆弱度的 colorbar */}
        {selectedLayer === 'structural_vulnerability' && (
          <div style={{
            marginTop: '8px',
            marginBottom: '16px',
            marginLeft: '12px',
            marginRight: '12px'
          }}>
            {(() => {
              const config = LAYER_CONFIGS.structural_vulnerability;
              if (config) {
                const gradient = generateLegendGradient(config);
                return (
                  <div>
                    <div style={{
                      height: '8px',
                      background: gradient,
                      borderRadius: '3px',
                      marginBottom: '4px'
                    }}></div>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '10px',
                      color: '#888'
                    }}>
                      <span>0% (無風險)</span>
                      <span>100% (極高風險)</span>
                    </div>
                  </div>
                );
              }
              return null;
            })()}
          </div>
        )}

        {/* 其他圖層 - 每個圖層選項後面跟著自己的 colorbar */}
        {otherLayers.map((layer) => (
          <div key={layer.id}>
            <RadioLayerToggle
              id={layer.id}
              label={layer.label}
              description={layer.description}
              icon={layer.icon}
              checked={selectedLayer === layer.id}
              onChange={() => handleLayerChange(layer.id)}
            />
            
            {/* 該圖層的 colorbar - 只在選中時顯示 */}
            {selectedLayer === layer.id && (
              <div style={{
                marginTop: '8px',
                marginBottom: '16px',
                marginLeft: '12px',
                marginRight: '12px'
              }}>
                {activeLegends.filter(legend => legend.layerType === layer.id || !legend.layerType).map((legend, index) => (
                  <div key={index}>
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
        ))}
      </div>
    </div>
  );
};

export default DataLayersModule;