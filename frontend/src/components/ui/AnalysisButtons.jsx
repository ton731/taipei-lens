import React from 'react';

const AnalysisButtons = ({
  onExecute,
  onClear,
  isExecuteDisabled = false,
  isClearDisabled = false,
  hasResults = false
}) => {
  return (
    <div style={{
      display: 'flex',
      gap: '8px',
      marginTop: '16px'
    }}>
      <button
        onClick={onExecute}
        disabled={isExecuteDisabled}
        style={{
          flex: 1,
          padding: '10px 16px',
          fontSize: '13px',
          fontWeight: '600',
          color: 'white',
          backgroundColor: isExecuteDisabled ? '#d1d5db' : '#d97706',
          border: 'none',
          borderRadius: '8px',
          cursor: isExecuteDisabled ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          boxShadow: isExecuteDisabled ? 'none' : '0 2px 8px rgba(217, 119, 6, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          outline: 'none'
        }}
        onMouseEnter={(e) => {
          if (!isExecuteDisabled) {
            e.target.style.backgroundColor = '#b45309';
            e.target.style.transform = 'translateY(-1px)';
            e.target.style.boxShadow = '0 4px 12px rgba(217, 119, 6, 0.4)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isExecuteDisabled) {
            e.target.style.backgroundColor = '#d97706';
            e.target.style.transform = 'translateY(0)';
            e.target.style.boxShadow = '0 2px 8px rgba(217, 119, 6, 0.3)';
          }
        }}
        onFocus={(e) => {
          if (!isExecuteDisabled) {
            e.target.style.boxShadow = '0 0 0 3px rgba(217, 119, 6, 0.3)';
          }
        }}
        onBlur={(e) => {
          if (!isExecuteDisabled) {
            e.target.style.boxShadow = '0 2px 8px rgba(217, 119, 6, 0.3)';
          }
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: 'white' }}>
          <polygon points="5 3 19 12 5 21 5 3" fill="currentColor"/>
        </svg>
        Execute
      </button>

      <button
        onClick={onClear}
        disabled={isClearDisabled || !hasResults}
        style={{
          flex: 1,
          padding: '10px 16px',
          fontSize: '13px',
          fontWeight: '600',
          color: (isClearDisabled || !hasResults) ? '#9ca3af' : '#6b7280',
          backgroundColor: (isClearDisabled || !hasResults) ? '#f3f4f6' : 'white',
          border: '1px solid #d1d5db',
          borderRadius: '8px',
          cursor: (isClearDisabled || !hasResults) ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          outline: 'none'
        }}
        onMouseEnter={(e) => {
          if (!isClearDisabled && hasResults) {
            e.target.style.backgroundColor = '#f3f4f6';
            e.target.style.borderColor = '#9ca3af';
          }
        }}
        onMouseLeave={(e) => {
          if (!isClearDisabled && hasResults) {
            e.target.style.backgroundColor = 'white';
            e.target.style.borderColor = '#d1d5db';
          }
        }}
        onFocus={(e) => {
          if (!isClearDisabled && hasResults) {
            e.target.style.boxShadow = '0 0 0 3px rgba(217, 119, 6, 0.2)';
            e.target.style.borderColor = '#d97706';
          }
        }}
        onBlur={(e) => {
          if (!isClearDisabled && hasResults) {
            e.target.style.boxShadow = 'none';
            e.target.style.borderColor = '#d1d5db';
          }
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: 'currentColor' }}>
          <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        Clear
      </button>
    </div>
  );
};

export default AnalysisButtons;