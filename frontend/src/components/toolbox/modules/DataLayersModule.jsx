import React from 'react';
import RadioLayerToggle from '../../ui/RadioLayerToggle';

const DataLayersModule = ({ onLayerChange, activeLegends = [], selectedLayer = null }) => {
  const layers = [
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

      {/* Legend display area - compact integrated design */}
      {activeLegends.length > 0 && (
        <div style={{
          marginTop: '12px',
          marginLeft: '12px',
          marginRight: '12px'
        }}>
          {activeLegends.map((legend, index) => (
            <div key={index}>
              {/* Gradient color scale display */}
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