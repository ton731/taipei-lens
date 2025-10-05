import React from 'react';

const InteractiveFormulaDisplay = ({ factors, onWeightChange }) => {
  // factors format: [{ name: 'Factor A', weight: 0.4 }, { name: 'Factor B', weight: 0.3 }, ...]
  // onWeightChange(index, newWeight) - Callback function when weight changes

  const handleWeightChange = (index, value) => {
    const newWeight = parseFloat(value) || 0;
    const clampedWeight = Math.max(0, Math.min(1, newWeight));

    if (onWeightChange) {
      onWeightChange(index, clampedWeight);
    }
  };

  return (
    <div style={{
      backgroundColor: '#f8f9ff',
      border: '1px solid #e0e7ff',
      borderRadius: '8px',
      padding: '14px 16px',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>

      <div style={{
        fontSize: '14px',
        color: '#374151',
        lineHeight: '1.8',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          flexWrap: 'wrap'
        }}>
          <span style={{ fontWeight: '600', color: '#d97706' }}>Priority Score =</span>
        </div>

        {factors.map((factor, index) => (
          <div key={index} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            paddingLeft: '16px',
            fontSize: '13px'
          }}>
            <span style={{ color: '#d97706', fontWeight: '600' }}>
              {index > 0 ? '+' : ' '}
            </span>
            <span style={{ color: '#6b7280' }}>(</span>

            {/* Editable weight input box - placed in front */}
            <input
              type="number"
              value={factor.weight.toFixed(2)}
              onChange={(e) => handleWeightChange(index, e.target.value)}
              min="0"
              max="1"
              step="0.01"
              style={{
                width: '70px',
                padding: '4px 8px',
                fontSize: '13px',
                fontWeight: '700',
                color: '#d97706',
                backgroundColor: '#fef3e7',
                border: '2px solid #d97706',
                borderRadius: '5px',
                textAlign: 'center',
                outline: 'none',
                cursor: 'text'
              }}
              onFocus={(e) => {
                e.target.style.boxShadow = '0 0 0 3px rgba(217, 119, 6, 0.2)';
              }}
              onBlur={(e) => {
                e.target.style.boxShadow = 'none';
              }}
            />

            <span style={{ color: '#6b7280' }}>×</span>
            <span style={{ color: '#374151', fontWeight: '500' }}>{factor.name}</span>
            <span style={{ color: '#6b7280' }}>)</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InteractiveFormulaDisplay;