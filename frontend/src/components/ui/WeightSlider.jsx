import React from 'react';

const WeightSlider = ({
  id,
  factorName,
  value,
  onChange,
  min = 0,
  max = 1,
  step = 0.01,
  disabled = false,
  icon
}) => {
  const displayValue = parseFloat(value).toFixed(2);
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div style={{
      width: '100%',
      padding: '4px 0', // Further reduced to 4px
      opacity: disabled ? 0.6 : 1,
      transition: 'opacity 0.3s ease'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '4px' // Further reduced to 4px
      }}>
        <span style={{ fontSize: '16px' }}>
          {icon}
        </span>
        <span style={{
          fontSize: '14px',
          fontWeight: '500',
          color: '#374151',
          flex: 1
        }}>
          {factorName}
        </span>
        <span style={{
          fontSize: '13px',
          color: '#d97706', // Deep orange
          backgroundColor: '#fef3e7', // Light orange background
          padding: '3px 8px',
          borderRadius: '4px',
          fontWeight: '500',
          minWidth: '50px',
          textAlign: 'center'
        }}>
          {displayValue}
        </span>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span style={{
          fontSize: '11px',
          color: '#9ca3af',
          minWidth: '15px'
        }}>
          0
        </span>

        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="range"
            id={id}
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={onChange}
            disabled={disabled}
            style={{
              width: '100%',
              height: '6px',
              borderRadius: '3px',
              background: `linear-gradient(to right, #d97706 0%, #d97706 ${percentage}%, #e5e7eb ${percentage}%, #e5e7eb 100%)`, // Deep orange slider
              outline: 'none',
              appearance: 'none',
              cursor: disabled ? 'not-allowed' : 'pointer',
              WebkitAppearance: 'none'
            }}
          />
          <style jsx>{`
            input[type="range"]::-webkit-slider-thumb {
              appearance: none;
              -webkit-appearance: none;
              width: 18px;
              height: 18px;
              border-radius: 50%;
              background: #d97706; // Deep orange slider button
              border: 2px solid white;
              box-shadow: 0 2px 6px rgba(0,0,0,0.2);
              cursor: ${disabled ? 'not-allowed' : 'pointer'};
              transition: transform 0.2s ease;
            }

            input[type="range"]::-webkit-slider-thumb:hover {
              transform: ${disabled ? 'none' : 'scale(1.1)'};
            }

            input[type="range"]::-moz-range-thumb {
              width: 18px;
              height: 18px;
              border-radius: 50%;
              background: #d97706; // Deep orange slider button
              border: 2px solid white;
              box-shadow: 0 2px 6px rgba(0,0,0,0.2);
              cursor: ${disabled ? 'not-allowed' : 'pointer'};
              border: none;
            }
          `}</style>
        </div>

        <span style={{
          fontSize: '11px',
          color: '#9ca3af',
          minWidth: '15px',
          textAlign: 'right'
        }}>
          1
        </span>
      </div>

    </div>
  );
};

export default WeightSlider;