import React from 'react';

const LoadingOverlay = ({ isLoading, message = "Loading map..." }) => {
  if (!isLoading) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.6)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,
      transition: 'opacity 0.3s ease-out'
    }}>
      {/* Spinning animation */}
      <div
        className="loading-spinner"
        style={{
          width: '60px',
          height: '60px',
          border: '4px solid rgba(255, 255, 255, 0.3)',
          borderTop: '4px solid #4264fb',
          borderRadius: '50%',
          marginBottom: '20px'
        }}
      />

      {/* Loading message */}
      <div style={{
        color: 'white',
        fontSize: '18px',
        fontWeight: '500',
        textAlign: 'center',
        marginBottom: '10px'
      }}>
        {message}
      </div>

      {/* Subtitle */}
      <div style={{
        color: 'rgba(255, 255, 255, 0.7)',
        fontSize: '14px',
        textAlign: 'center',
        maxWidth: '300px',
        lineHeight: '1.4'
      }}>
        Loading Taipei Urban Resilience Planning Platform
      </div>

      {/* CSS animation definition */}
      <style>{`
        .loading-spinner {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default LoadingOverlay;