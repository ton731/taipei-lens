import React from 'react';

const FormulaDisplay = ({ factors }) => {
  // factors 格式: [{ name: '因子A', weight: 0.4 }, { name: '因子B', weight: 0.3 }, ...]

  return (
    <div style={{
      backgroundColor: '#f8f9ff',
      border: '1px solid #e0e7ff',
      borderRadius: '8px',
      padding: '12px 16px',
      marginBottom: '16px',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        fontSize: '11px',
        fontWeight: '600',
        color: '#6b7280',
        marginBottom: '8px',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        計算公式
      </div>

      <div style={{
        fontSize: '13px',
        color: '#1f2937',
        lineHeight: '1.6',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '4px'
      }}>
        <span style={{ fontWeight: '600', color: '#4264fb' }}>分數 =</span>
        {factors.map((factor, index) => (
          <React.Fragment key={index}>
            <span>(</span>
            <span style={{ color: '#374151' }}>{factor.name}</span>
            <span> × </span>
            <span style={{
              backgroundColor: '#fef3e7',
              color: '#d97706',
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: '600',
              fontSize: '12px'
            }}>
              {factor.weight.toFixed(2)}
            </span>
            <span>)</span>
            {index < factors.length - 1 && <span style={{ color: '#d97706', fontWeight: '600' }}> + </span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default FormulaDisplay;