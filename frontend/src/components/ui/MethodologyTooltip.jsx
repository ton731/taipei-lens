import React, { useState, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom';

const MethodologyTooltip = ({ content }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef(null);

  useEffect(() => {
    if (showTooltip && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setTooltipPosition({
        top: rect.top,
        left: rect.right + 8
      });
    }
  }, [showTooltip]);

  return (
    <>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <button
          ref={buttonRef}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          style={{
            width: '18px',
            height: '18px',
            minWidth: '18px',
            minHeight: '18px',
            borderRadius: '50%',
            border: '1px solid #d97706',
            backgroundColor: '#fef3e7',
            color: '#d97706',
            fontSize: '11px',
            fontWeight: '600',
            cursor: 'help',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            flexShrink: 0,
            padding: '0',
            margin: '0',
            outline: 'none',
            boxSizing: 'border-box'
          }}
        >
          ?
        </button>
      </div>
      {showTooltip && ReactDOM.createPortal(
        <div
          style={{
            position: 'fixed',
            top: `${tooltipPosition.top}px`,
            left: `${tooltipPosition.left}px`,
            width: '280px',
            padding: '10px 12px',
            backgroundColor: '#1f2937',
            color: 'white',
            fontSize: '11px',
            borderRadius: '6px',
            lineHeight: '1.5',
            zIndex: 9999,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            whiteSpace: 'normal',
            textAlign: 'left',
            pointerEvents: 'none'
          }}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <div style={{
            fontWeight: '600',
            marginBottom: '6px',
            color: '#fbbf24'
          }}>
            Scientific Methodology
          </div>
          <div dangerouslySetInnerHTML={{ __html: content }} />
        </div>,
        document.body
      )}
    </>
  );
};

export default MethodologyTooltip;