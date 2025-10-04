import React from 'react';

const FactorCheckbox = ({
  id,
  checked,
  onChange,
  disabled = false,
  icon,
  label,
  description
}) => {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      padding: '12px 0',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.6 : 1,
      transition: 'opacity 0.2s ease'
    }}>
      <div style={{ position: 'relative', marginRight: '12px' }}>
        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={onChange}
          disabled={disabled}
          style={{ display: 'none' }}
        />
        <label
          htmlFor={id}
          style={{
            display: 'block',
            width: '20px',
            height: '20px',
            border: `2px solid ${checked ? '#4264fb' : '#d1d5db'}`,
            borderRadius: '4px',
            backgroundColor: checked ? '#4264fb' : 'white',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease',
            position: 'relative'
          }}
        >
          {checked && (
            <span style={{
              position: 'absolute',
              top: '2px',
              left: '5px',
              color: 'white',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              ✓
            </span>
          )}
        </label>
      </div>

      <div
        style={{ flex: 1, cursor: disabled ? 'not-allowed' : 'pointer' }}
        onClick={disabled ? undefined : onChange}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '2px'
        }}>
          <span style={{ fontSize: '16px' }}>
            {icon}
          </span>
          <span style={{
            fontSize: '14px',
            fontWeight: '500',
            color: '#333'
          }}>
            {label}
          </span>
        </div>
        {description && (
          <div style={{
            fontSize: '12px',
            color: '#666',
            marginLeft: '24px'
          }}>
            {description}
          </div>
        )}
      </div>
    </div>
  );
};

export default FactorCheckbox;