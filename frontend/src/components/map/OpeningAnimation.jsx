import { useEffect, useState, useRef } from 'react';
import { Source, Layer } from 'react-map-gl/mapbox';

// 全球主要都市的熱點位置（代表氣候變遷風險區域）
const GLOBAL_HOTSPOTS = [
  // 亞洲
  { id: 1, coordinates: [121.5654, 25.0330], name: 'Taipei' },        // 台北
  { id: 2, coordinates: [139.6917, 35.6895], name: 'Tokyo' },         // 東京
  { id: 3, coordinates: [116.4074, 39.9042], name: 'Beijing' },       // 北京
  { id: 4, coordinates: [121.4737, 31.2304], name: 'Shanghai' },      // 上海
  { id: 5, coordinates: [126.9780, 37.5665], name: 'Seoul' },         // 首爾
  { id: 6, coordinates: [103.8198, 1.3521], name: 'Singapore' },      // 新加坡
  { id: 7, coordinates: [77.2090, 28.6139], name: 'Delhi' },          // 德里
  { id: 8, coordinates: [72.8777, 19.0760], name: 'Mumbai' },         // 孟買
  { id: 9, coordinates: [100.5018, 13.7563], name: 'Bangkok' },       // 曼谷
  { id: 10, coordinates: [106.8456, -6.2088], name: 'Jakarta' },      // 雅加達
  { id: 11, coordinates: [114.1095, 22.3964], name: 'Hong Kong' },    // 香港
  { id: 12, coordinates: [55.2708, 25.2048], name: 'Dubai' },         // 杜拜

  // 歐洲
  { id: 13, coordinates: [-0.1278, 51.5074], name: 'London' },        // 倫敦
  { id: 14, coordinates: [2.3522, 48.8566], name: 'Paris' },          // 巴黎
  { id: 15, coordinates: [13.4050, 52.5200], name: 'Berlin' },        // 柏林
  { id: 16, coordinates: [37.6173, 55.7558], name: 'Moscow' },        // 莫斯科
  { id: 17, coordinates: [12.4964, 41.9028], name: 'Rome' },          // 羅馬
  { id: 18, coordinates: [-3.7038, 40.4168], name: 'Madrid' },        // 馬德里

  // 北美洲
  { id: 19, coordinates: [-74.0060, 40.7128], name: 'New York' },     // 紐約
  { id: 20, coordinates: [-118.2437, 34.0522], name: 'Los Angeles' }, // 洛杉磯
  { id: 21, coordinates: [-87.6298, 41.8781], name: 'Chicago' },      // 芝加哥
  { id: 22, coordinates: [-99.1332, 19.4326], name: 'Mexico City' },  // 墨西哥城
  { id: 23, coordinates: [-79.3832, 43.6532], name: 'Toronto' },      // 多倫多

  // 南美洲
  { id: 24, coordinates: [-43.1729, -22.9068], name: 'Rio' },         // 里約
  { id: 25, coordinates: [-46.6333, -23.5505], name: 'São Paulo' },   // 聖保羅
  { id: 26, coordinates: [-58.3816, -34.6037], name: 'Buenos Aires' },// 布宜諾斯艾利斯

  // 大洋洲
  { id: 27, coordinates: [151.2093, -33.8688], name: 'Sydney' },      // 雪梨
  { id: 28, coordinates: [144.9631, -37.8136], name: 'Melbourne' },   // 墨爾本

  // 非洲
  { id: 29, coordinates: [18.4241, -33.9249], name: 'Cape Town' },    // 開普敦
  { id: 30, coordinates: [31.2357, 30.0444], name: 'Cairo' },         // 開羅
  { id: 31, coordinates: [3.3792, 6.5244], name: 'Lagos' },           // 拉哥斯
];

const OpeningAnimation = ({ mapInstance, onAnimationComplete, onProjectionSwitch }) => {
  const [opacity, setOpacity] = useState(0);
  const animationFrameRef = useRef(null);
  const hasStartedRef = useRef(false); // 防止重複執行

  useEffect(() => {
    if (!mapInstance || hasStartedRef.current) return;

    hasStartedRef.current = true;
    console.log('開場動畫開始');

    // 設定為地球投影
    mapInstance.setProjection('globe');

    // 階段1：地球旋轉到亞洲上空
    const startRotation = () => {
      console.log('開始地球旋轉');
      mapInstance.easeTo({
        center: [121.5654, 25.0330],
        zoom: 2,
        pitch: 0,
        bearing: 0,
        duration: 4000,
        easing: (t) => t
      });

      // 使用事件驅動：等待旋轉完成後停留1秒
      mapInstance.once('moveend', () => {
        setTimeout(startFirstZoom, 1000);
      });
    };

    // 階段2：第一階段 zoom in 到台灣視角（降低 zoom 到 5，更穩定）
    const startFirstZoom = () => {
      console.log('執行第一階段 zoom in 到台灣視角');
      mapInstance.flyTo({
        center: [121.5654, 25.0330],
        zoom: 5,
        pitch: 0,
        bearing: 0,
        duration: 3000,
        essential: true
      });

      // 使用事件驅動：等待 zoom 完成後切換投影
      mapInstance.once('moveend', switchProjection);
    };

    // 階段3：切換投影到 mercator
    const switchProjection = () => {
      console.log('切換投影到 mercator');
      mapInstance.setProjection('mercator');

      // 通知 React 狀態更新
      if (onProjectionSwitch) {
        onProjectionSwitch();
      }

      // 縮短等待時間到 500ms（投影切換完成）
      setTimeout(startFinalZoom, 500);
    };

    // 階段4：第二階段 zoom in 到台北市最終視角
    const startFinalZoom = () => {
      console.log('繼續 zoom in 到台北市');
      mapInstance.flyTo({
        center: [121.5654, 25.0330],
        zoom: 14,
        pitch: 45,
        bearing: 0,
        duration: 3000,
        essential: true
      });

      // 使用事件驅動：等待 zoom 完成後觸發回調
      mapInstance.once('moveend', () => {
        console.log('Zoom in 完成');
        if (onAnimationComplete) {
          onAnimationComplete();
        }
      });
    };

    // 延遲 500ms 開始動畫
    setTimeout(startRotation, 500);

    // 清理函數
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [mapInstance, onAnimationComplete, onProjectionSwitch]);

  // 閃爍效果動畫 - 在 zoom in 時逐漸淡出
  useEffect(() => {
    let interval = setInterval(() => {
      setOpacity(prev => (prev === 0 ? 1 : 0));
    }, 800); // 每0.8秒閃爍一次

    // 5.5秒後開始淡出熱點（配合切換投影的時間）
    const fadeOutTimeout = setTimeout(() => {
      clearInterval(interval);
      // 逐漸淡出
      let fadeOpacity = 1;
      interval = setInterval(() => {
        fadeOpacity -= 0.1;
        if (fadeOpacity <= 0) {
          fadeOpacity = 0;
          clearInterval(interval);
        }
        setOpacity(fadeOpacity);
      }, 200);
    }, 5500);

    return () => {
      clearInterval(interval);
      clearTimeout(fadeOutTimeout);
    };
  }, []);

  // 建立 GeoJSON 數據
  const hotspotData = {
    type: 'FeatureCollection',
    features: GLOBAL_HOTSPOTS.map(spot => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: spot.coordinates
      },
      properties: {
        id: spot.id,
        name: spot.name
      }
    }))
  };

  return (
    <>
      {/* 熱點圓圈圖層 */}
      <Source id="hotspots" type="geojson" data={hotspotData}>
        {/* 外圈光暈效果 */}
        <Layer
          id="hotspots-glow"
          type="circle"
          paint={{
            'circle-radius': 25,
            'circle-color': '#ff4444',
            'circle-opacity': opacity * 0.3,
            'circle-blur': 1
          }}
        />
        {/* 中圈 */}
        <Layer
          id="hotspots-middle"
          type="circle"
          paint={{
            'circle-radius': 15,
            'circle-color': '#ff6666',
            'circle-opacity': opacity * 0.6
          }}
        />
        {/* 內圈核心 */}
        <Layer
          id="hotspots-core"
          type="circle"
          paint={{
            'circle-radius': 8,
            'circle-color': '#ffaa00',
            'circle-opacity': opacity * 0.9
          }}
        />
      </Source>
    </>
  );
};

export default OpeningAnimation;
