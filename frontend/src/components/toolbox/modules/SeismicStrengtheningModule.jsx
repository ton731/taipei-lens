import React, { useState } from 'react';
import PriorityScoreBlock from '../../ui/PriorityScoreBlock';
import ThresholdInput from '../../ui/ThresholdInput';
import AnalysisButtons from '../../ui/AnalysisButtons';

const SeismicStrengtheningModule = ({
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
  const MODULE_ID = 'seismicStrengthening'; // Module ID used to identify this module's analysis results

  // Use externally passed weights and threshold (from parent component's state)
  // Default to Public Works Bureau scenario (first scenario)
  const weights = externalWeights || { building_vulnerability: 0.50, site_amplification: 0.30, population_exposure: 0.20 };
  const threshold = externalThreshold !== undefined ? externalThreshold : 0.5;

  // Derive result status from analysisResult (don't use internal state)
  const hasResults = analysisResult !== null && analysisResult !== undefined;
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

        // Building Vulnerability: Extract from avg_fragility_curve JSON
        let buildingVulnerability = 0;
        if (props.avg_fragility_curve) {
          try {
            const fragilityCurve = JSON.parse(props.avg_fragility_curve);
            // Use intensity 6弱 earthquake damage probability
            buildingVulnerability = fragilityCurve['6弱'] || fragilityCurve['6weak'] || 0;
          } catch (error) {
            buildingVulnerability = 0;
          }
        }

        // Site Amplification Effect: Soil Liquefaction Potential Rating Score
        const siteAmplification = props.liq_risk || 0;

        // Population Exposure: 0.5×Population Density + 0.5×VIIRS Nighttime Light
        const popDensity = props.norm_population_density || 0;
        const viirs = props.norm_viirs_mean || 0;
        const populationExposure = 0.5 * popDensity + 0.5 * viirs;

        // Calculate weighted score
        const score =
          buildingVulnerability * weights.building_vulnerability +
          siteAmplification * weights.site_amplification +
          populationExposure * weights.population_exposure;

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


      // 3. Call callback function to update analysis results
      onAnalysisExecute(MODULE_ID, highlightedDistricts);

    } catch (error) {
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
    { name: 'Building Vulnerability', weight: weights.building_vulnerability },
    { name: 'Site Amplification Effect', weight: weights.site_amplification },
    { name: 'Population Exposure', weight: weights.population_exposure }
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
        Identify areas with the highest seismic damage risk that need priority structural reinforcement
      </div>

      <PriorityScoreBlock
        factors={factors}
        onWeightChange={handleWeightChange}
        onPresetSelect={handlePresetSelect}
        moduleType="seismicStrengthening"
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
          id="threshold-seismic"
          value={threshold}
          onChange={(e) => onConfigChange({ threshold: parseFloat(e.target.value) || 0 })}
        />

        {/* Analysis result display */}
        {hasResults && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            alignSelf: 'flex-start'
          }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '6px 12px',
              backgroundColor: resultCount > 0 ? '#fff7ed' : '#f3f4f6',
              borderRadius: '12px',
              fontSize: '13px',
              color: resultCount > 0 ? '#ea580c' : '#6b7280',
              marginTop: '2px'
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: resultCount > 0 ? '#f97316' : '#9ca3af', flexShrink: 0 }}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                <polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
              </svg>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontWeight: '600' }}>
                  {resultCount} priority strengthening areas identified
                </span>
                {resultCount === 0 && (
                  <span style={{ fontSize: '11px', color: '#6b7280', fontWeight: '400' }}>
                    Try lowering the threshold to identify more areas
                  </span>
                )}
              </div>
            </div>
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

export default SeismicStrengtheningModule;