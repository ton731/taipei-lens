import React, { useState } from 'react';
import AccordionItem from '../../ui/AccordionItem';
import ToggleSwitch from '../../ui/ToggleSwitch';

const HeatIslandModule = ({ isOpen, onToggleOpen }) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [showHeatMap, setShowHeatMap] = useState(false);
  const [showGreenery, setShowGreenery] = useState(false);

  const handleToggleEnabled = (e) => {
    const enabled = e.target.checked;
    setIsEnabled(enabled);

    // 如果關閉主開關，也關閉所有子選項
    if (!enabled) {
      setShowHeatMap(false);
      setShowGreenery(false);
    }

  };

  const handleHeatMapToggle = (e) => {
    const enabled = e.target.checked;
    setShowHeatMap(enabled);
  };

  const handleGreeneryToggle = (e) => {
    const enabled = e.target.checked;
    setShowGreenery(enabled);
  };

  return (
    <AccordionItem
      icon={
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: '#333' }}>
          <path d="M14 14.76V3a3 3 0 0 0-6 0v11.76a4 4 0 1 0 6 0z" stroke="currentColor" strokeWidth="2" fill="none"/>
          <circle cx="11" cy="17" r="2" stroke="currentColor" strokeWidth="2" fill="currentColor"/>
        </svg>
      }
      title="都市熱島與綠化分析"
      isOpen={isOpen}
      onToggleOpen={onToggleOpen}
      onToggleEnabled={handleToggleEnabled}
      isEnabled={isEnabled}
    >
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <div style={{
          fontSize: '13px',
          color: '#666',
          lineHeight: '1.4',
          marginBottom: '8px'
        }}>
          疊加顯示都市熱島效應與綠化分布，識別需要綠化降溫的區域。
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div style={{
            padding: '12px',
            backgroundColor: '#fff8f0',
            borderRadius: '6px',
            border: '1px solid #fed7aa'
          }}>
            <ToggleSwitch
              id="heat-map-toggle"
              label="都市熱島效應"
              checked={showHeatMap}
              onChange={handleHeatMapToggle}
              disabled={!isEnabled}
            />
            <div style={{
              fontSize: '11px',
              color: '#92400e',
              marginTop: '4px',
              marginLeft: '52px'
            }}>
              顯示 NASA 地表溫度熱力圖
            </div>
          </div>

          <div style={{
            padding: '12px',
            backgroundColor: '#f0fdf4',
            borderRadius: '6px',
            border: '1px solid #bbf7d0'
          }}>
            <ToggleSwitch
              id="greenery-toggle"
              label="都市綠化"
              checked={showGreenery}
              onChange={handleGreeneryToggle}
              disabled={!isEnabled}
            />
            <div style={{
              fontSize: '11px',
              color: '#15803d',
              marginTop: '4px',
              marginLeft: '52px'
            }}>
              顯示路樹與公園綠地分布
            </div>
          </div>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '12px',
          color: '#999',
          marginTop: '4px'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <div style={{
              width: '12px',
              height: '12px',
              background: 'linear-gradient(to right, #3b82f6, #ef4444)',
              borderRadius: '2px'
            }}></div>
            溫度分布
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <div style={{
              width: '12px',
              height: '12px',
              backgroundColor: '#22c55e',
              borderRadius: '50%'
            }}></div>
            綠化區域
          </div>
        </div>
      </div>
    </AccordionItem>
  );
};

export default HeatIslandModule;