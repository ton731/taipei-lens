import React, { useState } from 'react';
import InteractiveFormulaDisplay from '../../ui/InteractiveFormulaDisplay';
import ThresholdInput from '../../ui/ThresholdInput';
import AnalysisButtons from '../../ui/AnalysisButtons';
import RolePresetButtons from '../../ui/RolePresetButtons';

const SeismicStrengtheningModule = () => {
  const [weights, setWeights] = useState({
    building_vulnerability: 0.5,
    site_amplification: 0.3,
    population_exposure: 0.2
  });
  const [threshold, setThreshold] = useState(0.75);
  const [hasResults, setHasResults] = useState(false);

  const handleWeightChange = (index, newWeight) => {
    const weightKeys = Object.keys(weights);
    const updatedWeights = { ...weights };
    updatedWeights[weightKeys[index]] = newWeight;

    // If not the last factor, automatically adjust the last factor's weight
    if (index < weightKeys.length - 1) {
      const sumExceptLast = weightKeys
        .slice(0, -1)
        .reduce((sum, key) => sum + updatedWeights[key], 0);

      const lastKey = weightKeys[weightKeys.length - 1];
      updatedWeights[lastKey] = Math.max(0, Math.min(1, 1 - sumExceptLast));
    } else {
      // If adjusting the last factor, need to proportionally adjust other factors
      const otherKeys = weightKeys.slice(0, -1);
      const otherSum = otherKeys.reduce((sum, key) => sum + updatedWeights[key], 0);
      const remainingWeight = 1 - newWeight;

      if (otherSum > 0) {
        otherKeys.forEach(key => {
          updatedWeights[key] = (updatedWeights[key] / otherSum) * remainingWeight;
        });
      } else {
        // If the sum of previous factors is 0, distribute evenly
        const avgWeight = remainingWeight / otherKeys.length;
        otherKeys.forEach(key => {
          updatedWeights[key] = avgWeight;
        });
      }
    }

    setWeights(updatedWeights);
  };

  const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0);
  const isWeightValid = Math.abs(totalWeight - 1.0) < 0.01;

  const handleExecute = () => {
    if (!isWeightValid) {
      alert('Weight sum must equal 1, current sum is ' + totalWeight.toFixed(2));
      return;
    }
    setHasResults(true);
  };

  const handleClear = () => {
    setHasResults(false);
  };

  const handlePresetSelect = (presetWeights) => {
    setWeights(presetWeights);
  };

  const factors = [
    { name: 'Building Vulnerability', weight: weights.building_vulnerability },
    { name: 'Site Amplification Effect', weight: weights.site_amplification },
    { name: 'Population Exposure', weight: weights.population_exposure }
  ];


  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }}>
      <div style={{
        fontSize: '13px',
        color: '#6b7280',
        lineHeight: '1.4',
        marginBottom: '6px'
      }}>
        Identify areas with the highest seismic damage risk that need priority structural reinforcement
      </div>

      <RolePresetButtons
        onPresetSelect={handlePresetSelect}
        moduleType="seismicStrengthening"
        currentWeights={weights}
      />

      <InteractiveFormulaDisplay
        factors={factors}
        onWeightChange={handleWeightChange}
      />

      <ThresholdInput
        id="threshold-seismic"
        value={threshold}
        onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
      />

      <AnalysisButtons
        onExecute={handleExecute}
        onClear={handleClear}
        isExecuteDisabled={!isWeightValid}
        hasResults={hasResults}
      />

      {!isWeightValid && (
        <div style={{
          padding: '8px 10px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          fontSize: '11px',
          color: '#991b1b',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ color: '#dc2626' }}>
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
            <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="12" y1="16" x2="12.01" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Weight sum must equal 1.00
        </div>
      )}
    </div>
  );
};

export default SeismicStrengtheningModule;