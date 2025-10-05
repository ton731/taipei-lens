import React from 'react';
import RadioLayerToggle from '../../ui/RadioLayerToggle';
import StructuralVulnerabilityControl from '../../ui/StructuralVulnerabilityControl';
import { LAYER_CONFIGS, generateLegendGradient } from '../../../config/layerConfig';

const DataLayersModule = ({ onLayerChange, activeLegends = [], selectedLayer = null, earthquakeIntensity, onEarthquakeIntensityChange }) => {

  // NASA layers first
  const nasaLayers = [
    {
      id: 'lst',
      label: 'Surface Temperature',
      description: 'Land surface temperature distribution',
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
      id: 'utfvi',
      label: 'Thermal Comfort Index',
      description: 'Urban thermal field variance and comfort index',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2v10l3 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <circle cx="12" cy="18" r="4" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M8 18h8" stroke="currentColor" strokeWidth="1.5"/>
        </svg>
      )
    },
    {
      id: 'ndvi',
      label: 'Vegetation Index',
      description: 'Distribution of Normalized Difference Vegetation Index (NDVI)',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="currentColor" strokeWidth="2" fill="none"/>
          <polyline points="7.5,12 12,15 16.5,12" stroke="currentColor" strokeWidth="2" fill="none"/>
          <line x1="12" y1="15" x2="12" y2="21" stroke="currentColor" strokeWidth="2"/>
        </svg>
      )
    },
    {
      id: 'coverage_strict_300m',
      label: 'Green Space Accessibility',
      description: 'Green space coverage within 300m radius',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L2 7v10c0 5.55 3.84 10 9 11 5.16-1 9-5.45 9-11V7l-10-5z" stroke="currentColor" strokeWidth="2" fill="none"/>
          <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )
    },
    {
      id: 'viirs_mean',
      label: 'Nighttime Light',
      description: 'VIIRS nighttime light intensity distribution',
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
    }
  ];

  // Other local layers
  const localLayers = [
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
      id: 'liq_risk',
      label: 'Liquefaction Risk',
      description: 'Soil liquefaction risk distribution',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2v20m8-10H4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <path d="M8 8l8 8m0-8l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <rect x="6" y="6" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" rx="2"/>
        </svg>
      )
    }
  ];

  // Structural vulnerability layer
  const structuralVulnerabilityLayer = {
    id: 'structural_vulnerability',
    label: 'Structural Vulnerability',
    description: 'Structural collapse probability',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M12 2l3.5 7h7l-5.5 4 2 7-7-5-7 5 2-7-5.5-4h7z" stroke="currentColor" strokeWidth="2" fill="none"/>
        <path d="M8 16l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    )
  };

  // Combine NASA layers first, then structural vulnerability, then local layers
  const otherLayers = [...nasaLayers, structuralVulnerabilityLayer, ...localLayers];

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
        {/* All layers in order */}
        {otherLayers.map((layer) => {
          // NASA 圖層列表
          const nasaLayerIds = ['lst', 'utfvi', 'ndvi', 'coverage_strict_300m', 'viirs_mean'];
          const isNasaLayer = nasaLayerIds.includes(layer.id);
          
          return (
            <div key={layer.id}>
              <RadioLayerToggle
                id={layer.id}
                label={layer.label}
                description={layer.description}
                icon={layer.icon}
                checked={selectedLayer === layer.id}
                onChange={() => handleLayerChange(layer.id)}
                showNasaIcon={isNasaLayer}
              />

            {/* Special handling for Structural Vulnerability - Earthquake Intensity Control */}
            {selectedLayer === 'structural_vulnerability' && layer.id === 'structural_vulnerability' && earthquakeIntensity && onEarthquakeIntensityChange && (
              <div style={{ marginTop: '8px', marginBottom: '8px' }}>
                <StructuralVulnerabilityControl
                  earthquakeIntensity={earthquakeIntensity}
                  onIntensityChange={onEarthquakeIntensityChange}
                />
              </div>
            )}
            
            {/* Layer's colorbar - Only show when selected */}
            {selectedLayer === layer.id && (
              <div style={{
                marginTop: '8px',
                marginBottom: '16px',
                marginLeft: '12px',
                marginRight: '12px'
              }}>
                {/* Special handling for Structural Vulnerability colorbar */}
                {layer.id === 'structural_vulnerability' ? (
                  (() => {
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
                            <span>0% (No Risk)</span>
                            <span>100% (Extreme Risk)</span>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  })()
                ) : (
                  /* Regular colorbar for other layers */
                  activeLegends.filter(legend => legend.layerType === layer.id || !legend.layerType).map((legend, index) => (
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
                  ))
                )}
              </div>
            )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DataLayersModule;