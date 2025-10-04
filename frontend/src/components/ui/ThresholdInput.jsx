import React from 'react';

const ThresholdInput = ({
  id,
  value,
  onChange,
  disabled = false,
  min = 0,
  max = 1,
  step = 0.01
}) => {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      marginTop: '8px'
    }}>
      <label htmlFor={id} style={{
        fontSize: '13px',
        color: '#6b7280',
        fontWeight: '500',
        display: 'flex',
        alignItems: 'center',
        gap: '5px'
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: '#9ca3af' }}>
          <path d="M4 12h16m-7-7l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Highlight Threshold (Risk Score ≥)
      </label>

      <input
        type="number"
        id={id}
        value={value}
        onChange={onChange}
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        style={{
          width: '70px',
          padding: '5px 10px',
          fontSize: '14px',
          color: '#374151',
          backgroundColor: 'white',
          border: '1.5px solid #d1d5db',
          borderRadius: '5px',
          outline: 'none',
          textAlign: 'center',
          fontWeight: '600',
          cursor: disabled ? 'not-allowed' : 'text'
        }}
        onFocus={(e) => {
          if (!disabled) {
            e.target.style.border = '1.5px solid #d97706';
            e.target.style.boxShadow = '0 0 0 2px rgba(217, 119, 6, 0.15)';
          }
        }}
        onBlur={(e) => {
          e.target.style.border = '1.5px solid #d1d5db';
          e.target.style.boxShadow = 'none';
        }}
      />
    </div>
  );
};

export default ThresholdInput;