import React, { useState } from 'react';
import InteractiveFormulaDisplay from '../../ui/InteractiveFormulaDisplay';
import ThresholdInput from '../../ui/ThresholdInput';
import AnalysisButtons from '../../ui/AnalysisButtons';
import MethodologyTooltip from '../../ui/MethodologyTooltip';

const TestModule = ({
  mapInstance,
  statisticalAreaSourceLayer,
  onAnalysisExecute,
  onAnalysisClear,
  onClearDataLayer,
  weights: externalWeights,
  threshold: externalThreshold,
  onConfigChange,
  analysisResult
}) => {
  const MODULE_ID = 'test'; // Module ID used to identify this module's analysis results

  // Use externally passed weights and threshold (from parent component's state)
  const weights = externalWeights;
  const threshold = externalThreshold;

  // Derive result status from analysisResult (don't use internal state)
  const hasResults = analysisResult && analysisResult.length > 0;
  const resultCount = analysisResult ? analysisResult.length : 0;

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

    // Update parent component's state
    onConfigChange({ weights: updatedWeights });
  };

  const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0);
  const isWeightValid = Math.abs(totalWeight - 1.0) < 0.01;

  const handleExecute = () => {
    if (!isWeightValid) {
      alert('Weight sum must equal 1, current sum is ' + totalWeight.toFixed(2));
      return;
    }

    if (!mapInstance || !statisticalAreaSourceLayer) {
      console.error('Map instance or statistical area layer not ready');
      alert('Map has not finished loading, please try again later');
      return;
    }

    // Clear raw data layers to avoid layer stacking
    if (onClearDataLayer) {
      onClearDataLayer();
    }

    try {
      // 1. Query all statistical area features (using minimum statistical area data)
      const features = mapInstance.querySourceFeatures('statistical-areas', {
        sourceLayer: statisticalAreaSourceLayer
      });

      if (features.length === 0) {
        alert('Unable to retrieve statistical area data, please confirm map has loaded');
        return;
      }

      // 2. Calculate score for each statistical area and filter
      const highlightedDistricts = [];

      features.forEach(feature => {
        const props = feature.properties;

        // Use normalized data to calculate weighted score
        const normBuildingAge = props.norm_avg_building_age || 0;
        const normPopDensity = props.norm_population_density || 0;

        const score =
          normBuildingAge * weights.building_age +
          normPopDensity * weights.pop_density;

        // If score exceeds threshold, add to highlight list
        if (score >= threshold) {
          highlightedDistricts.push(props.CODEBASE);
        }
      });

      // 3. Call callback function to update analysis results
      onAnalysisExecute(MODULE_ID, highlightedDistricts);

    } catch (error) {
      console.error('Error occurred during analysis:', error);
      // Clear analysis results
      onAnalysisExecute(MODULE_ID, []);
    }
  };

  const handleClear = () => {
    onAnalysisClear(MODULE_ID);
  };

  const factors = [
    { name: 'Building Age', weight: weights.building_age },
    { name: 'Population Density', weight: weights.pop_density }
  ];

  const methodologyContent = `
    • <strong>Building Age</strong>: Test building age data<br/>
    • <strong>Population Density</strong>: Test population density data
  `;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      padding: '16px 20px'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '8px',
        marginBottom: '-2px'
      }}>
        <div style={{
          fontSize: '13px',
          color: '#6b7280',
          lineHeight: '1.4',
          flex: 1
        }}>
          Test Module: Backend API Integration Testing
        </div>
        <MethodologyTooltip content={methodologyContent} />
      </div>

      <InteractiveFormulaDisplay
        factors={factors}
        onWeightChange={handleWeightChange}
      />

      <div style={{
        borderTop: '1px solid #f3f4f6',
        paddingTop: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        <ThresholdInput
          id="threshold-test"
          value={threshold}
          onChange={(e) => onConfigChange({ threshold: parseFloat(e.target.value) || 0 })}
        />

        {/* Analysis result display - lightweight badge style, using blue theme to echo risk score */}
        {hasResults && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '7px',
            alignSelf: 'flex-start',
            padding: '6px 12px',
            backgroundColor: '#eff6ff',
            borderRadius: '12px',
            fontSize: '13px',
            color: '#1e40af',
            marginTop: '2px'
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: '#3b82f6', flexShrink: 0 }}>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
              <polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
            </svg>
            <span style={{ fontWeight: '600' }}>
              {resultCount} statistical areas matched
            </span>
          </div>
        )}

        <AnalysisButtons
          onExecute={handleExecute}
          onClear={handleClear}
          isExecuteDisabled={!isWeightValid}
          hasResults={hasResults}
        />

        {!isWeightValid && (
          <div style={{
            padding: '6px 10px',
            backgroundColor: '#fef2f2',
            borderRadius: '6px',
            fontSize: '10px',
            color: '#991b1b',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" style={{ color: '#dc2626', flexShrink: 0 }}>
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
              <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="12" y1="16" x2="12.01" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Weight sum must equal 1.00
          </div>
        )}
      </div>
    </div>
  );
};

export default TestModule;