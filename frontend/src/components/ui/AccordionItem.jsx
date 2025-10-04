import React from 'react';
import ToggleSwitch from './ToggleSwitch';

const AccordionItem = ({
  icon,
  title,
  isOpen,
  onToggleOpen,
  onToggleEnabled,
  isEnabled = false,
  children,
  disabled = false
}) => {
  return (
    <div style={{
      borderBottom: '1px solid #e5e5e5',
      overflow: 'hidden'
    }}>
      {/* Title row - includes icon, title, master switch and expand button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px',
        backgroundColor: isOpen ? '#f8f9ff' : 'transparent',
        cursor: 'pointer',
        transition: 'background-color 0.2s ease',
        borderLeft: isEnabled ? '3px solid #4264fb' : '3px solid transparent'
      }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            flex: 1,
            minWidth: 0
          }}
          onClick={onToggleOpen}
        >
          <span style={{
            fontSize: '16px',
            marginRight: '8px'
          }}>
            {icon}
          </span>

          <span style={{
            fontSize: '14px',
            fontWeight: '600',
            color: '#333',
            flex: 1,
            truncateOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            overflow: 'hidden'
          }}>
            {title}
          </span>

          {/* Expand/collapse arrow */}
          <span style={{
            fontSize: '12px',
            color: '#666',
            marginLeft: '8px',
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s ease'
          }}>
            ▼
          </span>
        </div>

        {/* Master switch */}
        <div style={{ marginLeft: '12px' }} onClick={(e) => e.stopPropagation()}>
          <ToggleSwitch
            id={`${title}-toggle`}
            checked={isEnabled}
            onChange={onToggleEnabled}
            disabled={disabled}
          />
        </div>
      </div>

      {/* Expanded content area */}
      <div style={{
        maxHeight: isOpen ? '300px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 0.3s ease-in-out',
        backgroundColor: '#fafbff'
      }}>
        <div style={{
          padding: isOpen ? '16px' : '0 16px',
          opacity: isOpen ? 1 : 0,
          transition: 'opacity 0.3s ease, padding 0.3s ease'
        }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default AccordionItem;