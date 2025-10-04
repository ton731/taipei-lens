import React from 'react';

const LegendPanel = ({ activeLegends = [] }) => {
  // Don't show panel if there are no active legends
  if (activeLegends.length === 0) {
    return null;
  }

  return (
    <div style={{
      position: 'absolute',
      bottom: '20px',
      right: '20px',
      zIndex: 1000,
      maxWidth: '280px',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderRadius: '12px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      overflow: 'hidden',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {/* Title bar */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid #e5e5e5',
        backgroundColor: 'rgba(66, 100, 251, 0.05)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span style={{ fontSize: '14px' }}>📊</span>
          <h4 style={{
            margin: 0,
            fontSize: '14px',
            fontWeight: '600',
            color: '#1a1a1a'
          }}>
            Legend
          </h4>
        </div>
      </div>

      {/* Legend content */}
      <div style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {activeLegends.map((legend, index) => (
          <div key={index}>
            {/* Legend title */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '8px'
            }}>
              <span style={{ fontSize: '12px' }}>
                {legend.icon}
              </span>
              <span style={{
                fontSize: '13px',
                fontWeight: '600',
                color: '#333'
              }}>
                {legend.title}
              </span>
            </div>

            {/* Legend items */}
            <div style={{
              display: 'flex',
              flexDirection: legend.type === 'gradient' ? 'column' : 'row',
              gap: legend.type === 'gradient' ? '4px' : '8px',
              flexWrap: 'wrap'
            }}>
              {legend.type === 'gradient' ? (
                // Gradient color scale display
                <div>
                  <div style={{
                    height: '8px',
                    background: legend.gradient,
                    borderRadius: '4px',
                    marginBottom: '4px'
                  }}></div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '10px',
                    color: '#666'
                  }}>
                    <span>{legend.minLabel}</span>
                    <span>{legend.maxLabel}</span>
                  </div>
                </div>
              ) : (
                // Discrete color items
                legend.items.map((item, itemIndex) => (
                  <div key={itemIndex} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px'
                  }}>
                    <div style={{
                      width: '12px',
                      height: '12px',
                      backgroundColor: item.color,
                      borderRadius: item.shape === 'circle' ? '50%' : '2px',
                      border: item.border ? '1px solid #ccc' : 'none'
                    }}></div>
                    <span style={{ color: '#555' }}>
                      {item.label}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LegendPanel;