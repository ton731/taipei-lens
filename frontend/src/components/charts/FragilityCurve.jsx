import React from 'react';

/**
 * FragilityCurve - Fragility Curve Chart Component
 * Rendered using pure SVG, displays building damage probability under different earthquake intensities
 */
const FragilityCurve = () => {
  // Mock data: Earthquake magnitude vs. Damage probability
  // X-axis: Earthquake magnitude 3-9
  // Y-axis: Damage probability 0-100%
  const mockData = [
    { magnitude: 3, damageProb: 2 },
    { magnitude: 4, damageProb: 8 },
    { magnitude: 5, damageProb: 25 },
    { magnitude: 6, damageProb: 55 },
    { magnitude: 7, damageProb: 85 },
    { magnitude: 8, damageProb: 95 },
    { magnitude: 9, damageProb: 99 }
  ];

  // SVG size settings
  const width = 200;
  const height = 120;
  const padding = { top: 15, right: 15, bottom: 25, left: 40 };

  // Chart area dimensions
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Data range
  const xMin = 3, xMax = 9;
  const yMin = 0, yMax = 100;

  // Coordinate transformation functions
  const getX = (magnitude) => {
    return padding.left + ((magnitude - xMin) / (xMax - xMin)) * chartWidth;
  };

  const getY = (damageProb) => {
    return padding.top + chartHeight - ((damageProb - yMin) / (yMax - yMin)) * chartHeight;
  };

  // Generate SVG path
  const pathData = mockData.map((point, index) => {
    const x = getX(point.magnitude);
    const y = getY(point.damageProb);
    return index === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
  }).join(' ');

  // Generate smooth curve (using quadratic Bezier curve)
  const smoothPathData = mockData.map((point, index, array) => {
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

  // X-axis ticks (3, 5, 7, 9)
  const xTicks = [3, 5, 7, 9];

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

      {/* Data points */}
      {mockData.map(point => {
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
        return (
          <text
            key={`x-label-${tick}`}
            x={x}
            y={padding.top + chartHeight + 15}
            textAnchor="middle"
            fontSize="9"
            fill="#666"
          >
            {tick}
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