import React from 'react';

/**
 * FragilityCurve - 易損性曲線圖表組件
 * 使用純 SVG 繪製，顯示建築物在不同地震強度下的損壞機率
 * @param {Object} fragilityCurveData - fragility curve 資料 {地震強度: 機率}
 */
const FragilityCurve = ({ fragilityCurveData }) => {
  // 處理真實資料，如果沒有資料則使用假資料
  const processData = () => {
    if (!fragilityCurveData || typeof fragilityCurveData !== 'object') {
      // 假資料：使用正確的地震強度範圍
      return [
        { magnitude: '3', displayValue: '3級', damageProb: 2 },
        { magnitude: '4', displayValue: '4級', damageProb: 8 },
        { magnitude: '5弱', displayValue: '5弱', damageProb: 25 },
        { magnitude: '5強', displayValue: '5強', damageProb: 40 },
        { magnitude: '6弱', displayValue: '6弱', damageProb: 55 },
        { magnitude: '6強', displayValue: '6強', damageProb: 75 },
        { magnitude: '7', displayValue: '7級', damageProb: 85 }
      ];
    }

    // 定義正確的地震強度順序
    const intensityOrder = ['3', '4', '5弱', '5強', '6弱', '6強', '7'];
    const intensityDisplayMap = {
      '3': '3級',
      '4': '4級', 
      '5弱': '5弱',
      '5強': '5強',
      '6弱': '6弱',
      '6強': '6強',
      '7': '7級'
    };

    // 將真實資料轉換為圖表格式，按照正確順序排列
    return intensityOrder
      .filter(intensity => fragilityCurveData.hasOwnProperty(intensity))
      .map(intensity => ({
        magnitude: intensity,
        displayValue: intensityDisplayMap[intensity],
        damageProb: (fragilityCurveData[intensity] || 0) * 100 // 轉換為百分比
      }));
  };

  const data = processData();

  // SVG size settings
  const width = 200;
  const height = 120;
  const padding = { top: 15, right: 15, bottom: 25, left: 40 };

  // Chart area dimensions
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 動態計算數據範圍
  const magnitudes = data.map(d => d.magnitude);
  const probs = data.map(d => d.damageProb);
  
  // 為地震強度建立索引映射 (0-based)
  const intensityIndexMap = {
    '3': 0,
    '4': 1, 
    '5弱': 2,
    '5強': 3,
    '6弱': 4,
    '6強': 5,
    '7': 6
  };
  
  const xMin = 0; // 第一個強度的索引
  const xMax = data.length - 1; // 最後一個強度的索引
  const yMin = 0;
  const yMax = 100;

  // 座標轉換函數 - 使用索引而非實際強度值
  const getX = (magnitude) => {
    const intensityOrder = ['3', '4', '5弱', '5強', '6弱', '6強', '7'];
    const dataIndex = data.findIndex(d => d.magnitude === magnitude);
    const normalizedIndex = dataIndex / Math.max(data.length - 1, 1); // 避免除以0
    return padding.left + normalizedIndex * chartWidth;
  };

  const getY = (damageProb) => {
    return padding.top + chartHeight - ((damageProb - yMin) / (yMax - yMin)) * chartHeight;
  };

  // Generate SVG path
  const pathData = data.map((point, index) => {
    const x = getX(point.magnitude);
    const y = getY(point.damageProb);
    return index === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
  }).join(' ');

  // Generate smooth curve (using quadratic Bezier curve)
  const smoothPathData = data.map((point, index, array) => {
    const x = getX(point.magnitude);
    const y = getY(point.damageProb);

    if (index === 0) {
      return `M ${x} ${y}`;
    }

    // Calculate control points to create smooth curve
    const prevPoint = array[index - 1];
    const prevX = getX(prevPoint.magnitude);
    const prevY = getY(prevPoint.damageProb);

    const controlX = (prevX + x) / 2;

    return `Q ${controlX} ${prevY}, ${x} ${y}`;
  }).join(' ');

  // Y-axis ticks (0%, 25%, 50%, 75%, 100%)
  const yTicks = [0, 25, 50, 75, 100];

  // 動態生成 X 軸刻度 - 使用實際的地震強度
  const generateXTicks = () => {
    if (data.length <= 4) {
      // 如果資料點少，直接用所有資料點作為刻度
      return data.map(d => d.magnitude);
    } else {
      // 如果資料點多，選擇部分刻度以避免擁擠
      const step = Math.max(1, Math.floor(data.length / 4));
      return data.filter((_, index) => index % step === 0 || index === data.length - 1)
                 .map(d => d.magnitude);
    }
  };
  
  const xTicks = generateXTicks();

  return (
    <svg
      width={width}
      height={height}
      style={{
        display: 'block',
        backgroundColor: '#fafafa',
        borderRadius: '4px'
      }}
    >
      {/* Background grid lines - Y axis */}
      {yTicks.map(tick => {
        const y = getY(tick);
        return (
          <line
            key={`y-grid-${tick}`}
            x1={padding.left}
            y1={y}
            x2={padding.left + chartWidth}
            y2={y}
            stroke="#e5e5e5"
            strokeWidth="0.5"
            strokeDasharray="2,2"
          />
        );
      })}

      {/* Background grid lines - X axis */}
      {xTicks.map(tick => {
        const x = getX(tick);
        return (
          <line
            key={`x-grid-${tick}`}
            x1={x}
            y1={padding.top}
            x2={x}
            y2={padding.top + chartHeight}
            stroke="#e5e5e5"
            strokeWidth="0.5"
            strokeDasharray="2,2"
          />
        );
      })}

      {/* X axis */}
      <line
        x1={padding.left}
        y1={padding.top + chartHeight}
        x2={padding.left + chartWidth}
        y2={padding.top + chartHeight}
        stroke="#999"
        strokeWidth="1.5"
      />

      {/* Y axis */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={padding.top + chartHeight}
        stroke="#999"
        strokeWidth="1.5"
      />

      {/* Fragility curve (smooth version) */}
      <path
        d={smoothPathData}
        fill="none"
        stroke="url(#curveGradient)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Define gradient color */}
      <defs>
        <linearGradient id="curveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" style={{ stopColor: '#ff6b35', stopOpacity: 1 }} />
          <stop offset="100%" style={{ stopColor: '#ef4444', stopOpacity: 1 }} />
        </linearGradient>
      </defs>

      {/* 數據點 */}
      {data.map(point => {
        const x = getX(point.magnitude);
        const y = getY(point.damageProb);
        return (
          <circle
            key={`point-${point.magnitude}`}
            cx={x}
            cy={y}
            r="3"
            fill="#fff"
            stroke="#ef4444"
            strokeWidth="2"
          />
        );
      })}

      {/* Y-axis tick labels */}
      {yTicks.map(tick => {
        const y = getY(tick);
        return (
          <text
            key={`y-label-${tick}`}
            x={padding.left - 8}
            y={y + 3}
            textAnchor="end"
            fontSize="9"
            fill="#666"
          >
            {tick}%
          </text>
        );
      })}

      {/* X-axis tick labels */}
      {xTicks.map(tick => {
        const x = getX(tick);
        const dataPoint = data.find(d => d.magnitude === tick);
        const displayLabel = dataPoint ? dataPoint.displayValue : tick;
        return (
          <text
            key={`x-label-${tick}`}
            x={x}
            y={padding.top + chartHeight + 15}
            textAnchor="middle"
            fontSize="9"
            fill="#666"
          >
            {displayLabel}
          </text>
        );
      })}

      {/* Y-axis title */}
      <text
        x={8}
        y={padding.top + chartHeight / 2}
        textAnchor="middle"
        fontSize="10"
        fill="#444"
        fontWeight="500"
        transform={`rotate(-90 8 ${padding.top + chartHeight / 2})`}
      >
        Damage Prob.
      </text>

      {/* X-axis title */}
      <text
        x={padding.left + chartWidth / 2}
        y={height - 1}
        textAnchor="middle"
        fontSize="10"
        fill="#444"
        fontWeight="500"
      >
        Magnitude
      </text>
    </svg>
  );
};

export default FragilityCurve;