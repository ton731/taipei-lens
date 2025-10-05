import React from 'react';

const RadioLayerToggle = ({
  id,
  label,
  description,
  checked,
  onChange,
  icon,
  disabled = false,
  showNasaIcon = false
}) => {
  return (
    <label
      htmlFor={id}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px 12px',
        backgroundColor: checked ? '#fef3e7' : 'white',
        border: checked ? '2px solid #d97706' : '1px solid #e5e7eb',
        borderRadius: '8px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.2s ease',
        marginBottom: '6px',
        opacity: disabled ? 0.6 : 1
      }}
      onMouseEnter={(e) => {
        if (!disabled && !checked) {
          e.currentTarget.style.backgroundColor = '#fafbff';
          e.currentTarget.style.borderColor = '#d1d5db';
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled && !checked) {
          e.currentTarget.style.backgroundColor = 'white';
          e.currentTarget.style.borderColor = '#e5e7eb';
        }
      }}
    >
      <input
        type="radio"
        id={id}
        checked={checked}
        onChange={() => {}} // Empty function, actual handling in onClick
        onClick={onChange}  // Use onClick to handle clicks, so it can trigger even when already selected
        disabled={disabled}
        style={{
          width: '16px',
          height: '16px',
          accentColor: '#d97706',
          cursor: disabled ? 'not-allowed' : 'pointer',
          flexShrink: 0
        }}
      />

      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        {icon && (
          <span style={{ fontSize: '16px', color: checked ? '#d97706' : '#6b7280', flexShrink: 0 }}>
            {icon}
          </span>
        )}
        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: '6px',
          flexWrap: 'wrap'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <span style={{
              fontSize: '13px',
              fontWeight: '600',
              color: checked ? '#92400e' : '#374151'
            }}>
              {label}
            </span>
            {showNasaIcon && (
              <img 
                src="/nasa.png" 
                alt="NASA" 
                width="18" 
                height="18"
                style={{ 
                  flexShrink: 0,
                  objectFit: 'contain', // 保持原始比例，不變形
                  opacity: checked ? 1 : 0.8,
                  transition: 'opacity 0.2s ease'
                }} 
              />
            )}
          </div>
          {description && (
            <span style={{
              fontSize: '11px',
              color: checked ? '#b45309' : '#9ca3af',
              lineHeight: '1.4'
            }}>
              {description}
            </span>
          )}
        </div>
      </div>
    </label>
  );
};

export default RadioLayerToggle;