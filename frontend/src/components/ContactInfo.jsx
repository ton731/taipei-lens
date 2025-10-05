import React, { useState } from 'react';
import { getContactArray } from '../constants/contactInfo';

const ContactInfo = ({ onIconClick }) => {
  const [isHovered, setIsHovered] = useState(false);
  const contactData = getContactArray();

  const containerStyle = {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    zIndex: 1001,
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const iconStyle = {
    width: '50px',
    height: '50px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    backgroundColor: '#ff8c42',
    borderRadius: '50%',
    padding: '10px',
    boxShadow: '0 2px 8px rgba(255, 140, 66, 0.3)',
    transform: isHovered ? 'scale(1.1)' : 'scale(1)',
    '&:hover': {
      transform: 'scale(1.1)'
    }
  };

  const cardStyle = {
    position: 'absolute',
    bottom: '30px',
    right: '0',
    backgroundColor: 'white',
    border: '1px solid #e1e5e9',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    padding: '12px 16px',
    minWidth: '340px',
    opacity: isHovered ? 1 : 0,
    visibility: isHovered ? 'visible' : 'hidden',
    transform: isHovered ? 'translateY(0)' : 'translateY(10px)',
    transition: 'all 0.2s ease'
  };

  const headerStyle = {
    fontSize: '14px',
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: '8px',
    borderBottom: '1px solid #ecf0f1',
    paddingBottom: '6px'
  };

  const contactItemStyle = {
    fontSize: '12px',
    color: '#34495e',
    marginBottom: '4px',
    lineHeight: '1.4'
  };

  const nameStyle = {
    fontWeight: '500',
    color: '#2c3e50'
  };

  const emailStyle = {
    color: '#7f8c8d',
    fontFamily: 'monospace'
  };

  return (
    <div 
      style={containerStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 貓咪圖標 */}
      <svg 
        style={iconStyle}
        viewBox="0 0 24 24" 
        fill="white" 
        xmlns="http://www.w3.org/2000/svg"
        onClick={(e) => {
          e.stopPropagation();
          if (onIconClick) {
            onIconClick();
          }
        }}
      >
        {/* 貓咪頭部主體 - 橢圓形更可愛 */}
        <ellipse cx="12" cy="12.5" rx="8" ry="7.5" fill="#ff8c42"/>
        
        {/* 貓咪耳朵 - 圓潤三角形 */}
        <path d="M4 8C4 5 6 2 9 2C10.5 2 11 4 11 5.5C11 7 9.5 8 8 8C6 8 4 6.5 4 8Z" fill="#ff8c42"/>
        <path d="M13 8C13 5 15 2 18 2C19.5 2 20 4 20 5.5C20 7 18.5 8 17 8C15 8 13 6.5 13 8Z" fill="#ff8c42"/>
        
        {/* 耳朵內側橘色 */}
        <ellipse cx="8" cy="5.5" rx="1.5" ry="2" fill="#ff6b1a"/>
        <ellipse cx="17" cy="5.5" rx="1.5" ry="2" fill="#ff6b1a"/>
        
        {/* 貓咪眼睛 - 簡單黑色 */}
        <ellipse cx="9" cy="11" rx="1.5" ry="2" fill="black"/>
        <ellipse cx="15" cy="11" rx="1.5" ry="2" fill="black"/>
        
        {/* 貓咪鼻子 - 心形 */}
        <path d="M12 14C10.8 13.2 10.1 13.5 10.1 14.2C10.1 14.9 10.8 15.3 12 15.3C13.2 15.3 13.9 14.9 13.9 14.2C13.9 13.5 13.2 13.2 12 14Z" fill="black"/>
        
        {/* 貓咪嘴巴 - 可愛弧線 */}
        <path d="M12 15.3C10.5 16.8 9 16.4 8.2 15.7" stroke="black" strokeWidth="0.8" fill="none" strokeLinecap="round"/>
        <path d="M12 15.3C13.5 16.8 15 16.4 15.8 15.7" stroke="black" strokeWidth="0.8" fill="none" strokeLinecap="round"/>
        
        {/* 貓咪鬍鬚 - 優雅弧線 */}
        <path d="M4 11C5.5 10.7 7 10.9 8.5 11" stroke="black" strokeWidth="0.6" fill="none" strokeLinecap="round"/>
        <path d="M3.5 12.5C5 12.3 6.5 12.5 8 12.7" stroke="black" strokeWidth="0.6" fill="none" strokeLinecap="round"/>
        <path d="M4 14C5.5 14.2 7 14 8.5 13.8" stroke="black" strokeWidth="0.6" fill="none" strokeLinecap="round"/>
        
        <path d="M15.5 11C17 10.9 18.5 10.7 20 11" stroke="black" strokeWidth="0.6" fill="none" strokeLinecap="round"/>
        <path d="M16 12.7C17.5 12.5 19 12.3 20.5 12.5" stroke="black" strokeWidth="0.6" fill="none" strokeLinecap="round"/>
        <path d="M15.5 13.8C17 14 18.5 14.2 20 14" stroke="black" strokeWidth="0.6" fill="none" strokeLinecap="round"/>
        
        {/* 臉頰腮紅 */}
        <ellipse cx="5.5" cy="13" rx="1.2" ry="1" fill="#ff69b4" opacity="0.4"/>
        <ellipse cx="18.5" cy="13" rx="1.2" ry="1" fill="#ff69b4" opacity="0.4"/>
      </svg>

      {/* 聯絡資訊卡片 */}
      <div style={cardStyle}>
        <div style={headerStyle}>Contact Information</div>
        {contactData.map((contact, index) => (
          <div key={index} style={contactItemStyle}>
            <span style={nameStyle}>{contact.name}</span>
            <span>, </span>
            <span style={emailStyle}>{contact.email}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ContactInfo;