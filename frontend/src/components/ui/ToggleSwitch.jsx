import React from 'react';

const ToggleSwitch = ({ id, checked, onChange, disabled = false, label }) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ position: 'relative', display: 'inline-block' }}>
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
            width: '44px',
            height: '24px',
            backgroundColor: checked ? '#4264fb' : '#e0e0e0',
            borderRadius: '12px',
            position: 'relative',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.3s ease',
            opacity: disabled ? 0.5 : 1
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: '2px',
              left: checked ? '22px' : '2px',
              width: '20px',
              height: '20px',
              backgroundColor: 'white',
              borderRadius: '50%',
              transition: 'left 0.3s ease',
              boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
            }}
          />
        </label>
      </div>
      {label && (
        <span style={{
          fontSize: '14px',
          color: '#333',
          fontWeight: '500'
        }}>
          {label}
        </span>
      )}
    </div>
  );
};

export default ToggleSwitch;