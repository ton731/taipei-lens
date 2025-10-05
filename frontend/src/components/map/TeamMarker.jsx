import React from 'react';
import { Marker, Popup } from 'react-map-gl/mapbox';
import { getContactArray } from '../../constants/contactInfo';

const TeamMarker = ({ longitude, latitude, showPopup, onClose }) => {
  const contactData = getContactArray();
  
  // 只在 showPopup 為 true 時才渲染整個組件
  if (!showPopup) return null;
  
  return (
    <>
      {/* 地圖標記點 */}
      <Marker 
        longitude={longitude} 
        latitude={latitude}
        anchor="bottom"
      >
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          cursor: 'pointer'
        }}>
          {/* 標記圖釘 */}
          <svg
            width="48"
            height="64"
            viewBox="0 0 48 64"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{
              filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))',
              animation: 'bounce 2s ease-in-out infinite'
            }}
          >
            {/* 外圈 */}
            <circle cx="24" cy="24" r="22" fill="#ff8c42" stroke="white" strokeWidth="3"/>
            {/* 內圈 */}
            <circle cx="24" cy="24" r="18" fill="white"/>
            {/* 貓咪圖案 */}
            <g transform="translate(24, 24)">
              {/* 貓咪頭部 */}
              <ellipse cx="0" cy="0" rx="8" ry="7" fill="#ff8c42"/>
              {/* 貓咪耳朵 */}
              <path d="M-6 -6L-4 -9L-2 -6Z" fill="#ff8c42"/>
              <path d="M2 -6L4 -9L6 -6Z" fill="#ff8c42"/>
              {/* 貓咪眼睛 */}
              <circle cx="-2" cy="-1" r="1" fill="white"/>
              <circle cx="2" cy="-1" r="1" fill="white"/>
            </g>
            {/* 圖釘尖端 */}
            <path d="M24 46L12 32L36 32Z" fill="#ff8c42"/>
            <path d="M24 46L20 32L28 32Z" fill="#ff6b1a"/>
          </svg>
        </div>
      </Marker>

      {/* Popup 顯示團隊資訊 */}
      <Popup
          longitude={longitude}
          latitude={latitude}
          closeButton={true}
          closeOnClick={false}
          onClose={onClose}
          anchor="bottom"
          offset={[0, -65]}
          maxWidth="400px"
          style={{ 
            zIndex: 1002,
            borderRadius: '12px'
          }}
        >
          <div style={{
            padding: '12px',
            backgroundColor: 'white',
            borderRadius: '10px',
            width: '280px',
            fontFamily: 'system-ui, -apple-system, sans-serif'
          }}>
            {/* 標題 */}
            <h3 style={{
              margin: '0 0 10px 0',
              fontSize: '16px',
              fontWeight: '600',
              color: '#2c3e50',
              textAlign: 'center'
            }}>
              🚀 Development Team
            </h3>

            {/* 團隊照片 */}
            <div style={{
              marginBottom: '10px',
              borderRadius: '6px',
              overflow: 'hidden',
              boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
              height: '120px',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              backgroundColor: '#f8f9fa'
            }}>
              <img 
                src="/team_photo.jpg" 
                alt="Team Photo" 
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  display: 'block'
                }}
              />
            </div>

            {/* 位置標示 */}
            <div style={{
              fontSize: '10px',
              color: '#6c757d',
              textAlign: 'center',
              marginBottom: '8px',
              padding: '4px',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px'
            }}>
              📍 National Taiwan University
            </div>
            
            {/* 聯絡資訊 */}
            <div style={{
              fontSize: '11px'
            }}>
              {contactData.map((contact, index) => (
                <div key={index} style={{
                  backgroundColor: '#f8f9fa',
                  padding: '5px 8px',
                  borderRadius: '5px',
                  marginBottom: '4px'
                }}>
                  <div style={{ fontWeight: '600', color: '#2c3e50' }}>
                    {contact.name}
                  </div>
                  <div style={{ 
                    color: '#0066cc', 
                    fontSize: '10px'
                  }}>
                    {contact.email}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Popup>

      <style>
        {`
          @keyframes bounce {
            0%, 100% {
              transform: translateY(0);
            }
            50% {
              transform: translateY(-8px);
            }
          }
          
          /* 自定義 Mapbox popup 關閉按鈕樣式 */
          .mapboxgl-popup-close-button {
            color: #495057 !important;
            font-size: 20px !important;
            padding: 4px 8px !important;
            font-weight: 400 !important;
            opacity: 0.8 !important;
          }
          
          .mapboxgl-popup-close-button:hover {
            background-color: rgba(0, 0, 0, 0.05) !important;
            opacity: 1 !important;
            color: #212529 !important;
          }
        `}
      </style>
    </>
  );
};

export default TeamMarker;