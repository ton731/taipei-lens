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
  const MODULE_ID = 'test'; // 模組 ID，用於標識此模組的分析結果

  // 使用外部傳入的 weights 和 threshold (來自父組件的 state)
  const weights = externalWeights;
  const threshold = externalThreshold;

  // 從 analysisResult 推導出結果狀態（不使用內部 state）
  const hasResults = analysisResult && analysisResult.length > 0;
  const resultCount = analysisResult ? analysisResult.length : 0;

  const handleWeightChange = (index, newWeight) => {
    const weightKeys = Object.keys(weights);
    const updatedWeights = { ...weights };
    updatedWeights[weightKeys[index]] = newWeight;

    // 如果不是最後一個因子，自動調整最後一個因子的權重
    if (index < weightKeys.length - 1) {
      const sumExceptLast = weightKeys
        .slice(0, -1)
        .reduce((sum, key) => sum + updatedWeights[key], 0);

      const lastKey = weightKeys[weightKeys.length - 1];
      updatedWeights[lastKey] = Math.max(0, Math.min(1, 1 - sumExceptLast));
    } else {
      // 如果調整的是最後一個因子，需要按比例調整其他因子
      const otherKeys = weightKeys.slice(0, -1);
      const otherSum = otherKeys.reduce((sum, key) => sum + updatedWeights[key], 0);
      const remainingWeight = 1 - newWeight;

      if (otherSum > 0) {
        otherKeys.forEach(key => {
          updatedWeights[key] = (updatedWeights[key] / otherSum) * remainingWeight;
        });
      } else {
        // 如果前面的因子總和為0，平均分配
        const avgWeight = remainingWeight / otherKeys.length;
        otherKeys.forEach(key => {
          updatedWeights[key] = avgWeight;
        });
      }
    }

    // 更新父組件的 state
    onConfigChange({ weights: updatedWeights });
  };

  const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0);
  const isWeightValid = Math.abs(totalWeight - 1.0) < 0.01;

  const handleExecute = () => {
    if (!isWeightValid) {
      alert('權重總和必須等於 1，目前總和為 ' + totalWeight.toFixed(2));
      return;
    }

    if (!mapInstance || !statisticalAreaSourceLayer) {
      console.error('地圖實例或統計區圖層未準備好');
      alert('地圖尚未載入完成，請稍後再試');
      return;
    }

    // 清除原始數據圖層，避免圖層疊加
    if (onClearDataLayer) {
      onClearDataLayer();
    }

    try {
      // 1. 查詢所有統計區的 features（使用最小統計區域資料）
      const features = mapInstance.querySourceFeatures('statistical-areas', {
        sourceLayer: statisticalAreaSourceLayer
      });

      if (features.length === 0) {
        alert('無法取得統計區資料，請確認地圖已載入');
        return;
      }

      // 2. 計算每個統計區的分數並篩選
      const highlightedDistricts = [];

      features.forEach(feature => {
        const props = feature.properties;

        // 使用標準化資料計算加權分數
        const normBuildingAge = props.norm_avg_building_age || 0;
        const normPopDensity = props.norm_population_density || 0;

        const score =
          normBuildingAge * weights.building_age +
          normPopDensity * weights.pop_density;

        // 如果分數超過閥值，加入 highlight 列表
        if (score >= threshold) {
          highlightedDistricts.push(props.CODEBASE);
        }
      });

      // 3. 呼叫回調函式更新分析結果
      onAnalysisExecute(MODULE_ID, highlightedDistricts);

    } catch (error) {
      console.error('分析過程發生錯誤:', error);
      // 清除分析結果
      onAnalysisExecute(MODULE_ID, []);
    }
  };

  const handleClear = () => {
    onAnalysisClear(MODULE_ID);
  };

  const factors = [
    { name: '建築物年齡', weight: weights.building_age },
    { name: '人口密度', weight: weights.pop_density }
  ];

  const methodologyContent = `
    • <strong>建築物年齡</strong>：測試用建築物年齡數據<br/>
    • <strong>人口密度</strong>：測試用人口密度數據
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
          測試模組：串接後端API測試
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

        {/* 分析結果顯示 - 輕量 badge 樣式，使用藍色系呼應風險分數 */}
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
              符合 {resultCount} 個統計區
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
            權重總和必須等於 1.00
          </div>
        )}
      </div>
    </div>
  );
};

export default TestModule;