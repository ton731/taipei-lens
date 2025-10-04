import React from 'react';
import FragilityCurve from '../charts/FragilityCurve';

/**
 * Building Popup Component
 * @param {Object} props.data - Hover information
 */
const BuildingPopup = ({ data }) => {
  const displayFields = ['height', 'floor', 'area'];

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
      <FragilityCurve />
    </div>
  );
};

export default BuildingPopup;
