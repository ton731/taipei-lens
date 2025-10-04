import React from 'react';

const WeightInput = ({
  id,
  label,
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
      justifyContent: 'space-between',
      padding: '8px 12px',
      backgroundColor: '#fafbff',
      borderRadius: '6px',
      marginBottom: '8px',
      opacity: disabled ? 0.6 : 1
    }}>
      <label htmlFor={id} style={{
        fontSize: '13px',
        color: '#374151',
        fontWeight: '500',
        flex: 1
      }}>
        {label}
      </label>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span style={{
          fontSize: '12px',
          color: '#6b7280'
        }}>
          權重:
        </span>
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
            padding: '6px 8px',
            fontSize: '13px',
            color: '#1f2937',
            backgroundColor: 'white',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            outline: 'none',
            textAlign: 'center',
            fontWeight: '600',
            cursor: disabled ? 'not-allowed' : 'text'
          }}
          onFocus={(e) => {
            if (!disabled) {
              e.target.style.borderColor = '#d97706';
              e.target.style.boxShadow = '0 0 0 3px rgba(217, 119, 6, 0.1)';
            }
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#d1d5db';
            e.target.style.boxShadow = 'none';
          }}
        />
      </div>
    </div>
  );
};

export default WeightInput;