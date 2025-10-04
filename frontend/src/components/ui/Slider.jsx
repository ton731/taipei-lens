import React from 'react';

const Slider = ({
  id,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  unit = '',
  disabled = false
}) => {
  return (
    <div style={{ width: '100%' }}>
      {label && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px'
        }}>
          <label
            htmlFor={id}
            style={{
              fontSize: '14px',
              fontWeight: '500',
              color: '#333'
            }}
          >
            {label}
          </label>
          <span style={{
            fontSize: '13px',
            color: '#666',
            backgroundColor: '#f5f5f5',
            padding: '2px 8px',
            borderRadius: '4px'
          }}>
            {value}{unit}
          </span>
        </div>
      )}

      <div style={{ position: 'relative', width: '100%' }}>
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
            background: `linear-gradient(to right, #4264fb 0%, #4264fb ${((value - min) / (max - min)) * 100}%, #e0e0e0 ${((value - min) / (max - min)) * 100}%, #e0e0e0 100%)`,
            outline: 'none',
            appearance: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.5 : 1,
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
            background: #4264fb;
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
            background: #4264fb;
            border: 2px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            cursor: ${disabled ? 'not-allowed' : 'pointer'};
            border: none;
          }
        `}</style>
      </div>
    </div>
  );
};

export default Slider;