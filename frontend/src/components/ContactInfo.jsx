import React, { useState } from 'react';
import { getContactArray } from '../constants/contactInfo';

const ContactInfo = () => {
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
    width: '32px',
    height: '32px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    filter: isHovered ? 'brightness(0.6)' : 'brightness(0.8)',
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
      {/* 信封圖標 */}
      <svg 
        style={iconStyle}
        viewBox="0 0 24 24" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
      >
        <path 
          d="M3 8L10.89 13.26C11.2187 13.4793 11.6049 13.5963 12 13.5963C12.3951 13.5963 12.7813 13.4793 13.11 13.26L21 8M5 19H19C19.5304 19 20.0391 18.7893 20.4142 18.4142C20.7893 18.0391 21 17.5304 21 17V7C21 6.46957 20.7893 5.96086 20.4142 5.58579C20.0391 5.21071 19.5304 5 19 5H5C4.46957 5 3.96086 5.21071 3.58579 5.58579C3.21071 5.96086 3 6.46957 3 7V17C3 17.5304 3.21071 18.0391 3.58579 18.4142C3.96086 18.7893 4.46957 19 5 19Z" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        />
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