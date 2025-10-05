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
        {/* 貓咪頭部 */}
        <ellipse cx="12" cy="13" rx="6" ry="5" fill="white"/>
        
        {/* 貓咪耳朵 */}
        <path d="M8 9L10 6L12 9Z" fill="white"/>
        <path d="M12 9L14 6L16 9Z" fill="white"/>
        
        {/* 貓咪眼睛 */}
        <circle cx="10" cy="12" r="0.8" fill="black"/>
        <circle cx="14" cy="12" r="0.8" fill="black"/>
        
        {/* 貓咪鼻子 */}
        <path d="M12 14L11.5 15L12.5 15Z" fill="pink"/>
        
        {/* 貓咪嘴巴 */}
        <path d="M12 15C11 16 10 16 9.5 15.5" stroke="black" strokeWidth="0.5" fill="none"/>
        <path d="M12 15C13 16 14 16 14.5 15.5" stroke="black" strokeWidth="0.5" fill="none"/>
        
        {/* 貓咪鬍鬚 */}
        <line x1="7" y1="13" x2="9" y2="13" stroke="black" strokeWidth="0.3"/>
        <line x1="7.5" y1="14" x2="9" y2="14" stroke="black" strokeWidth="0.3"/>
        <line x1="15" y1="13" x2="17" y2="13" stroke="black" strokeWidth="0.3"/>
        <line x1="15" y1="14" x2="16.5" y2="14" stroke="black" strokeWidth="0.3"/>
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