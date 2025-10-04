import React, { useState } from 'react';
import AccordionItem from '../../ui/AccordionItem';
import Slider from '../../ui/Slider';

const SeismicRiskModule = ({ isOpen, onToggleOpen }) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [intensity, setIntensity] = useState(5);

  const handleToggleEnabled = (e) => {
    setIsEnabled(e.target.checked);
  };

  const handleIntensityChange = (e) => {
    const newIntensity = parseFloat(e.target.value);
    setIntensity(newIntensity);
  };

  return (
    <AccordionItem
      icon={
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: '#333' }}>
          <path d="M2 12h3l2-8 4 16 4-12 2 4h5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      }
      title="地震風險評估"
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
          調整地震強度以模擬不同震度下的建築物損壞風險。建築物顏色將從低風險（綠色）到高風險（紅色）變化。
        </div>

        <Slider
          id="seismic-intensity"
          label="地震強度"
          value={intensity}
          onChange={handleIntensityChange}
          min={1}
          max={7}
          step={0.5}
          unit=" 級"
          disabled={!isEnabled}
        />

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
              backgroundColor: '#22c55e',
              borderRadius: '2px'
            }}></div>
            低風險
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <div style={{
              width: '12px',
              height: '12px',
              backgroundColor: '#eab308',
              borderRadius: '2px'
            }}></div>
            中風險
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <div style={{
              width: '12px',
              height: '12px',
              backgroundColor: '#ef4444',
              borderRadius: '2px'
            }}></div>
            高風險
          </div>
        </div>
      </div>
    </AccordionItem>
  );
};

export default SeismicRiskModule;