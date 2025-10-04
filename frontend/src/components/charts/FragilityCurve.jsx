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
      // 假資料：地震規模 vs 損壞機率
      return [
        { magnitude: 3, damageProb: 2 },
        { magnitude: 4, damageProb: 8 },
        { magnitude: 5, damageProb: 25 },
        { magnitude: 6, damageProb: 55 },
        { magnitude: 7, damageProb: 85 },
        { magnitude: 8, damageProb: 95 },
        { magnitude: 9, damageProb: 99 }
      ];
    }

    // 將真實資料轉換為圖表格式
    const intensities = Object.keys(fragilityCurveData)
      .map(k => parseFloat(k))
      .filter(k => !isNaN(k))
      .sort((a, b) => a - b);

    return intensities.map(intensity => ({
      magnitude: intensity,
      damageProb: (fragilityCurveData[intensity.toString()] || 0) * 100 // 轉換為百分比
    }));
  };

  const data = processData();

  // SVG 尺寸設定
  const width = 200;
  const height = 120;
  const padding = { top: 15, right: 15, bottom: 25, left: 40 };

  // 繪圖區域尺寸
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 動態計算數據範圍
  const magnitudes = data.map(d => d.magnitude);
  const probs = data.map(d => d.damageProb);
  
  const xMin = Math.min(...magnitudes, 3);
  const xMax = Math.max(...magnitudes, 9);
  const yMin = 0;
  const yMax = 100;

  // 座標轉換函數
  const getX = (magnitude) => {
    return padding.left + ((magnitude - xMin) / (xMax - xMin)) * chartWidth;
  };

  const getY = (damageProb) => {
    return padding.top + chartHeight - ((damageProb - yMin) / (yMax - yMin)) * chartHeight;
  };

  // 生成 SVG 路徑
  const pathData = data.map((point, index) => {
    const x = getX(point.magnitude);
    const y = getY(point.damageProb);
    return index === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
  }).join(' ');

  // 生成平滑曲線（使用二次貝茲曲線）
  const smoothPathData = data.map((point, index, array) => {
    const x = getX(point.magnitude);
    const y = getY(point.damageProb);

    if (index === 0) {
      return `M ${x} ${y}`;
    }

    // 計算控制點以創造平滑曲線
    const prevPoint = array[index - 1];
    const prevX = getX(prevPoint.magnitude);
    const prevY = getY(prevPoint.damageProb);

    const controlX = (prevX + x) / 2;

    return `Q ${controlX} ${prevY}, ${x} ${y}`;
  }).join(' ');

  // Y軸刻度（0%, 25%, 50%, 75%, 100%）
  const yTicks = [0, 25, 50, 75, 100];

  // 動態生成 X 軸刻度
  const generateXTicks = () => {
    if (data.length <= 4) {
      // 如果資料點少，直接用資料點作為刻度
      return magnitudes;
    } else {
      // 如果資料點多，選擇均勻分布的刻度
      const range = xMax - xMin;
      const step = range / 3;
      return [xMin, xMin + step, xMin + 2 * step, xMax].map(v => Math.round(v * 10) / 10);
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
      {/* 背景網格線 - Y軸 */}
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

      {/* 背景網格線 - X軸 */}
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

      {/* X軸 */}
      <line
        x1={padding.left}
        y1={padding.top + chartHeight}
        x2={padding.left + chartWidth}
        y2={padding.top + chartHeight}
        stroke="#999"
        strokeWidth="1.5"
      />

      {/* Y軸 */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={padding.top + chartHeight}
        stroke="#999"
        strokeWidth="1.5"
      />

      {/* 易損性曲線（平滑版） */}
      <path
        d={smoothPathData}
        fill="none"
        stroke="url(#curveGradient)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* 定義漸層色 */}
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

      {/* Y軸刻度標籤 */}
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

      {/* X軸刻度標籤 */}
      {xTicks.map(tick => {
        const x = getX(tick);
        return (
          <text
            key={`x-label-${tick}`}
            x={x}
            y={padding.top + chartHeight + 15}
            textAnchor="middle"
            fontSize="9"
            fill="#666"
          >
            {tick}級
          </text>
        );
      })}

      {/* Y軸標題 */}
      <text
        x={8}
        y={padding.top + chartHeight / 2}
        textAnchor="middle"
        fontSize="10"
        fill="#444"
        fontWeight="500"
        transform={`rotate(-90 8 ${padding.top + chartHeight / 2})`}
      >
        損壞機率
      </text>

      {/* X軸標題 */}
      <text
        x={padding.left + chartWidth / 2}
        y={height - 1}
        textAnchor="middle"
        fontSize="10"
        fill="#444"
        fontWeight="500"
      >
        地震規模
      </text>
    </svg>
  );
};

export default FragilityCurve;