import React, { useState } from 'react';
import InteractiveFormulaDisplay from '../../ui/InteractiveFormulaDisplay';
import ThresholdInput from '../../ui/ThresholdInput';
import AnalysisButtons from '../../ui/AnalysisButtons';
import RolePresetButtons from '../../ui/RolePresetButtons';

const RoadGreeningModule = ({
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
  const MODULE_ID = 'roadGreening'; // Module ID used to identify this module's analysis results

  // Use externally passed weights and threshold (from parent component's state)
  // Default to Environmental Protection Bureau scenario (first scenario)
  const weights = externalWeights || { thermal_stress: 0.50, greening_potential: 0.30, population_benefit: 0.20 };
  const threshold = externalThreshold !== undefined ? externalThreshold : 0.8;

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
    console.log('RoadGreening Execute clicked!');
    console.log('Props check:', { mapInstance: !!mapInstance, statisticalAreaSourceLayer, weights, threshold });
    
    if (!isWeightValid) {
      alert('Weight sum must equal 1, current sum is ' + totalWeight.toFixed(2));
      return;
    }

    if (!mapInstance || !statisticalAreaSourceLayer) {
      console.error('Map instance or statistical area layer not ready', { mapInstance: !!mapInstance, statisticalAreaSourceLayer });
      alert('Map has not finished loading, please try again later');
      return;
    }

    // Clear raw data layers to avoid layer stacking
    if (onClearDataLayer) {
      onClearDataLayer();
    }

    try {
      // 1. Query all statistical area features
      const features = mapInstance.querySourceFeatures('statistical-areas', {
        sourceLayer: statisticalAreaSourceLayer
      });

      if (features.length === 0) {
        alert('Unable to retrieve statistical area data, please confirm map has loaded');
        return;
      }

      // 2. Calculate score for each statistical area and filter
      const highlightedDistricts = [];
      const scores = [];

      features.forEach(feature => {
        const props = feature.properties;

        // Thermal Stress: norm_utfvi (Urban Thermal Field Variance Index normalized)
        const thermalStress = props.norm_utfvi || 0;

        // Greening Potential: (1 - ndvi_mean) - areas with low vegetation coverage
        const ndvi = props.ndvi_mean || 0;
        const greeningPotential = 1 - ndvi;

        // Population Benefit: 0.5×Population Density + 0.5×VIIRS Nighttime Light
        const popDensity = props.norm_population_density || 0;
        const viirs = props.norm_viirs_mean || 0;
        const populationBenefit = 0.5 * popDensity + 0.5 * viirs;

        // Calculate weighted score
        const score =
          thermalStress * weights.thermal_stress +
          greeningPotential * weights.greening_potential +
          populationBenefit * weights.population_benefit;

        scores.push(score);

        // If score exceeds threshold, add to highlight list
        if (score >= threshold) {
          highlightedDistricts.push(props.CODEBASE);
        }
      });

      // Calculate statistics for debugging
      const maxScore = Math.max(...scores);
      const minScore = Math.min(...scores);
      const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;

      console.log(`Road Greening Analysis: Found ${highlightedDistricts.length} qualifying areas out of ${features.length} total areas`);
      console.log('Score statistics:', { min: minScore.toFixed(3), max: maxScore.toFixed(3), avg: avgScore.toFixed(3) });
      console.log('Threshold used:', threshold);
      console.log('Weights used:', weights);
      console.log('Sample data for first area:', features[0]?.properties);

      // 3. Call callback function to update analysis results
      onAnalysisExecute(MODULE_ID, highlightedDistricts);

    } catch (error) {
      console.error('Error occurred during road greening analysis:', error);
      // Clear analysis results
      onAnalysisExecute(MODULE_ID, []);
    }
  };

  const handleClear = () => {
    onAnalysisClear(MODULE_ID);
  };

  const handlePresetSelect = (presetWeights) => {
    onConfigChange({ weights: presetWeights });
  };

  const factors = [
    { name: 'Thermal Stress', weight: weights.thermal_stress },
    { name: 'Greening Potential', weight: weights.greening_potential },
    { name: 'Population Benefit', weight: weights.population_benefit }
  ];


  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      padding: '16px 20px'
    }}>
      <div style={{
        fontSize: '13px',
        color: '#6b7280',
        lineHeight: '1.4',
        marginBottom: '6px'
      }}>
        Identify areas most in need of cooling and environmental improvement through tree planting to optimize urban greening strategies
      </div>

      <InteractiveFormulaDisplay
        factors={factors}
        onWeightChange={handleWeightChange}
      />

      <RolePresetButtons
        onPresetSelect={handlePresetSelect}
        moduleType="roadGreening"
        currentWeights={weights}
      />

      <div style={{
        borderTop: '1px solid #f3f4f6',
        paddingTop: '6px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <ThresholdInput
          id="threshold-road-greening"
          value={threshold}
          onChange={(e) => onConfigChange({ threshold: parseFloat(e.target.value) || 0 })}
        />

        {/* Analysis result display */}
        {hasResults && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '7px',
            alignSelf: 'flex-start',
            padding: '6px 12px',
            backgroundColor: '#fff7ed',
            borderRadius: '12px',
            fontSize: '13px',
            color: '#ea580c',
            marginTop: '2px'
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: '#f97316', flexShrink: 0 }}>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
              <polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
            </svg>
            <span style={{ fontWeight: '600' }}>
              {resultCount} priority greening areas identified
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

export default RoadGreeningModule;