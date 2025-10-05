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
          {/* 可愛貓咪頭標記 */}
          <svg
            width="42"
            height="58"
            viewBox="0 0 42 58"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{
              filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))',
              animation: 'bounce 2s ease-in-out infinite'
            }}
          >
            {/* 貓咪頭部主體 - 橢圓形更可愛 */}
            <ellipse cx="21" cy="19" rx="16" ry="15" fill="#ff8c42" stroke="white" strokeWidth="2.5"/>
            
            {/* 貓咪耳朵 - 圓潤三角形 */}
            <path d="M8 12C8 8 11 4 15 4C17 4 18 6 18 8C18 10 16 12 14 12C11 12 8 10 8 12Z" fill="#ff8c42" stroke="white" strokeWidth="2"/>
            <path d="M24 12C24 8 27 4 31 4C33 4 34 6 34 8C34 10 32 12 30 12C27 12 24 10 24 12Z" fill="#ff8c42" stroke="white" strokeWidth="2"/>
            
            {/* 耳朵內側橘色 */}
            <ellipse cx="14" cy="9" rx="2.5" ry="3" fill="#ff6b1a"/>
            <ellipse cx="28" cy="9" rx="2.5" ry="3" fill="#ff6b1a"/>
            
            {/* 貓咪眼睛 - 簡單黑色 */}
            <ellipse cx="16" cy="17" rx="2.5" ry="3" fill="black"/>
            <ellipse cx="26" cy="17" rx="2.5" ry="3" fill="black"/>
            
            {/* 貓咪鼻子 - 心形 */}
            <path d="M21 22C19.5 21 18.5 21.5 18.5 22.5C18.5 23.5 19.5 24 21 24C22.5 24 23.5 23.5 23.5 22.5C23.5 21.5 22.5 21 21 22Z" fill="black"/>
            
            {/* 貓咪嘴巴 - 可愛弧線 */}
            <path d="M21 24C19 26 17 25.5 16 24.5" stroke="#2c3e50" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
            <path d="M21 24C23 26 25 25.5 26 24.5" stroke="#2c3e50" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
            
            {/* 貓咪鬍鬚 - 優雅弧線 */}
            <path d="M9 18C11 17.5 13 17.8 15 18" stroke="#2c3e50" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            <path d="M8 20C10 19.8 12 20 14 20.2" stroke="#2c3e50" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            <path d="M9 22C11 22.2 13 22 15 21.8" stroke="#2c3e50" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            
            <path d="M27 18C29 17.8 31 17.5 33 18" stroke="#2c3e50" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            <path d="M28 20.2C30 20 32 19.8 34 20" stroke="#2c3e50" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            <path d="M27 21.8C29 22 31 22.2 33 22" stroke="#2c3e50" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            
            {/* 臉頰腮紅 */}
            <ellipse cx="11" cy="21" rx="2" ry="1.5" fill="#ff69b4" opacity="0.4"/>
            <ellipse cx="31" cy="21" rx="2" ry="1.5" fill="#ff69b4" opacity="0.4"/>
            
            {/* 指向箭頭 */}
            <path d="M21 45L14 38L28 38Z" fill="#ff8c42" stroke="white" strokeWidth="2"/>
            <path d="M21 45L17 38L25 38Z" fill="#ff6b1a"/>
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
            borderRadius: '18px',
            filter: 'drop-shadow(0 8px 20px rgba(0, 0, 0, 0.25))'
          }}
        >
          <div style={{
            padding: '16px',
            backgroundColor: 'white',
            borderRadius: '18px',
            width: '300px',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
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
              height: '150px',
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
              fontSize: '13px'
            }}>
              {contactData.map((contact, index) => (
                <div key={index} style={{
                  backgroundColor: '#f8f9fa',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  marginBottom: '6px'
                }}>
                  <div style={{ 
                    fontWeight: '600', 
                    color: '#2c3e50',
                    fontSize: '14px',
                    marginBottom: '2px'
                  }}>
                    {contact.name}
                  </div>
                  <div style={{ 
                    color: '#0066cc', 
                    fontSize: '12px'
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
          
          /* 移除 Mapbox popup 外框 */
          .mapboxgl-popup-content {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            border-radius: 0 !important;
          }
          
          /* 自定義 Mapbox popup 關閉按鈕樣式 */
          .mapboxgl-popup-close-button {
            color: #495057 !important;
            font-size: 20px !important;
            padding: 4px 8px !important;
            font-weight: 400 !important;
            opacity: 0.8 !important;
            right: 8px !important;
            top: 8px !important;
          }
          
          .mapboxgl-popup-close-button:hover {
            background-color: rgba(0, 0, 0, 0.05) !important;
            opacity: 1 !important;
            color: #212529 !important;
          }
          
          /* 移除 popup 尖角 */
          .mapboxgl-popup-tip {
            display: none !important;
          }
        `}
      </style>
    </>
  );
};

export default TeamMarker;