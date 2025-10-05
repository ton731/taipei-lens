import React, { useState } from 'react';
import DataLayersModule from './modules/DataLayersModule';
import RoadGreeningModule from './modules/RoadGreeningModule';
import SeismicStrengtheningModule from './modules/SeismicStrengtheningModule';
import ParkSitingModule from './modules/ParkSitingModule';
import UrbanRenewalModule from './modules/UrbanRenewalModule';
import TestModule from './modules/TestModule';

const ToolboxPanel = ({
  onMouseEnter,
  onDataLayerChange,
  activeLegends,
  selectedDataLayer,
  mapInstance,
  districtSourceLayer,
  statisticalAreaSourceLayer,
  onAnalysisExecute,
  onAnalysisClear,
  onClearDataLayer,
  moduleConfigs,
  onModuleConfigChange,
  analysisResults,
  earthquakeIntensity,
  onEarthquakeIntensityChange
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [openSection, setOpenSection] = useState(null); // 'data', 'renovation', 'reconstruction', 'test'
  const [openSubModule, setOpenSubModule] = useState(null); // 'road_greening', 'seismic_strengthening', 'park_siting', 'urban_renewal'

  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleToggleSection = (section) => {
    if (openSection === section) {
      setOpenSection(null);
      setOpenSubModule(null);
    } else {
      setOpenSection(section);
      setOpenSubModule(null);
    }
  };

  const handleToggleSubModule = (subModule) => {
    if (openSubModule === subModule) {
      setOpenSubModule(null);
    } else {
      setOpenSubModule(subModule);
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: '50%',
        left: '20px',
        transform: 'translateY(-50%)',
        zIndex: 1000,
        maxHeight: 'calc(100vh - 40px)',
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'flex-start'
      }}
      onMouseEnter={onMouseEnter}
    >
      {/* 主控制面板 */}
      <div style={{
        width: isCollapsed ? '0px' : '400px',
        maxHeight: 'calc(100vh - 40px)',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderRadius: '12px',
        boxShadow: '0 12px 48px rgba(0, 0, 0, 0.25), 0 6px 24px rgba(0, 0, 0, 0.18)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        overflow: 'hidden',
        transition: 'width 0.3s ease',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        {!isCollapsed && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%'
          }}>
            {/* 標題欄 */}
            <div style={{
              padding: '18px 20px',
              borderBottom: '1px solid #e5e5e5',
              backgroundColor: 'rgba(217, 119, 6, 0.05)'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: '#333' }}>
                  <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" strokeWidth="2" fill="none"/>
                  <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" stroke="currentColor" strokeWidth="2" fill="none"/>
                  <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" strokeWidth="2"/>
                </svg>
                <h3 style={{
                  margin: 0,
                  fontSize: '16px',
                  fontWeight: '600',
                  color: '#1a1a1a'
                }}>
                  Planner's Toolbox
                </h3>
              </div>
              <div style={{
                fontSize: '12px',
                color: '#666',
                marginTop: '4px'
              }}>
                Urban Resilience Planning Analysis Tools
              </div>
            </div>

            {/* Accordion Menu */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              overflowX: 'hidden',
              maxHeight: 'calc(100vh - 160px)',
              scrollbarWidth: 'thin',
              scrollbarColor: '#d97706 #f1f1f1'
            }}>
              {/* 1. Data Layers */}
              <AccordionSection
                title="Data Layers"
                icon={(
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2" fill="none"/>
                    <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none"/>
                    <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none"/>
                  </svg>
                )}
                isOpen={openSection === 'data'}
                onToggle={() => handleToggleSection('data')}
              >
                <DataLayersModule
                  onLayerChange={onDataLayerChange}
                  activeLegends={activeLegends}
                  selectedLayer={selectedDataLayer}
                  earthquakeIntensity={earthquakeIntensity}
                  onEarthquakeIntensityChange={onEarthquakeIntensityChange}
                />
              </AccordionSection>

              {/* 2. Renovation Analysis Module */}
              <AccordionSection
                title="Renovation: Regional Strengthening Strategy"
                icon={(
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" stroke="currentColor" strokeWidth="2" fill="none"/>
                  </svg>
                )}
                isOpen={openSection === 'renovation'}
                onToggle={() => handleToggleSection('renovation')}
              >
                <div style={{ padding: '0' }}>
                  {/* Sub-Module 2.1: Road Greening Priority Analysis */}
                  <SubModuleAccordion
                    title="Road Greening Priority Analysis"
                    icon={(
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="currentColor" strokeWidth="2" fill="none"/>
                        <polyline points="3.27 6.96 12 12.01 20.73 6.96" stroke="currentColor" strokeWidth="2" fill="none"/>
                        <line x1="12" y1="22.08" x2="12" y2="12" stroke="currentColor" strokeWidth="2"/>
                      </svg>
                    )}
                    isOpen={openSubModule === 'road_greening'}
                    onToggle={() => handleToggleSubModule('road_greening')}
                  >
                    <RoadGreeningModule />
                  </SubModuleAccordion>

                  {/* Sub-Module 2.2: Building Seismic Retrofit Urgency Assessment */}
                  <SubModuleAccordion
                    title="Building Seismic Retrofit Urgency Assessment"
                    icon={(
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <path d="M2 12h3l2-8 4 16 4-12 2 4h5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                    isOpen={openSubModule === 'seismic_strengthening'}
                    onToggle={() => handleToggleSubModule('seismic_strengthening')}
                  >
                    <SeismicStrengtheningModule />
                  </SubModuleAccordion>
                </div>
              </AccordionSection>

              {/* 3. Reconstruction Analysis Module */}
              <AccordionSection
                title="Reconstruction: Urban Regeneration Strategy"
                icon={(
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="3" width="7" height="7" stroke="currentColor" strokeWidth="2" fill="none"/>
                    <rect x="14" y="3" width="7" height="7" stroke="currentColor" strokeWidth="2" fill="none"/>
                    <rect x="14" y="14" width="7" height="7" stroke="currentColor" strokeWidth="2" fill="none"/>
                    <rect x="3" y="14" width="7" height="7" stroke="currentColor" strokeWidth="2" fill="none"/>
                  </svg>
                )}
                isOpen={openSection === 'reconstruction'}
                onToggle={() => handleToggleSection('reconstruction')}
              >
                <div style={{ padding: '0' }}>
                  {/* Sub-Module 3.1: Park Site Suitability Analysis */}
                  <SubModuleAccordion
                    title="Park Site Suitability Analysis"
                    icon={(
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <path d="M12 2a9 9 0 0 1 9 9c0 6-9 13-9 13S3 17 3 11a9 9 0 0 1 9-9z" stroke="currentColor" strokeWidth="2" fill="none"/>
                        <circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="2" fill="none"/>
                      </svg>
                    )}
                    isOpen={openSubModule === 'park_siting'}
                    onToggle={() => handleToggleSubModule('park_siting')}
                  >
                    <ParkSitingModule />
                  </SubModuleAccordion>

                  {/* Sub-Module 3.2: Urban Renewal Priority Assessment */}
                  <SubModuleAccordion
                    title="Urban Renewal Priority Assessment"
                    icon={(
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
                        <polyline points="12 6 12 12 16 14" stroke="currentColor" strokeWidth="2" fill="none"/>
                      </svg>
                    )}
                    isOpen={openSubModule === 'urban_renewal'}
                    onToggle={() => handleToggleSubModule('urban_renewal')}
                  >
                    <UrbanRenewalModule
                      mapInstance={mapInstance}
                      statisticalAreaSourceLayer={statisticalAreaSourceLayer}
                      onAnalysisExecute={onAnalysisExecute}
                      onAnalysisClear={onAnalysisClear}
                      onClearDataLayer={onClearDataLayer}
                      weights={moduleConfigs.urbanRenewal.weights}
                      threshold={moduleConfigs.urbanRenewal.threshold}
                      onConfigChange={(config) => onModuleConfigChange('urbanRenewal', config)}
                      analysisResult={analysisResults.urbanRenewal}
                    />
                  </SubModuleAccordion>
                </div>
              </AccordionSection>

              {/* 4. Test Module */}
              <AccordionSection
                title="Test Module"
                icon={(
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M9 11l3 3L22 4" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
                isOpen={openSection === 'test'}
                onToggle={() => handleToggleSection('test')}
              >
                <TestModule
                  mapInstance={mapInstance}
                  statisticalAreaSourceLayer={statisticalAreaSourceLayer}
                  onAnalysisExecute={onAnalysisExecute}
                  onAnalysisClear={onAnalysisClear}
                  onClearDataLayer={onClearDataLayer}
                  weights={moduleConfigs.test.weights}
                  threshold={moduleConfigs.test.threshold}
                  onConfigChange={(config) => onModuleConfigChange('test', config)}
                  analysisResult={analysisResults.test}
                />
              </AccordionSection>
            </div>

            {/* Footer Information
            <div style={{
              padding: '12px 20px',
              borderTop: '1px solid #e5e5e5',
              backgroundColor: 'rgba(248, 249, 251, 0.8)',
              fontSize: '11px',
              color: '#888',
              textAlign: 'center'
            }}>
              Select an analysis module to explore Taipei's urban resilience
            </div> */}
          </div>
        )}
      </div>

      {/* Collapse/Expand Button */}
      <button
        onClick={handleToggleCollapse}
        style={{
          marginLeft: '8px',
          width: '32px',
          height: isCollapsed ? '120px' : '32px',
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          borderRadius: '8px',
          boxShadow: isCollapsed
            ? '0 8px 32px rgba(0, 0, 0, 0.25), 0 4px 16px rgba(0, 0, 0, 0.15)'
            : '0 6px 24px rgba(0, 0, 0, 0.2), 0 3px 12px rgba(0, 0, 0, 0.12)',
          backdropFilter: 'blur(8px)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '14px',
          color: '#d97706',
          transition: 'all 0.3s ease',
          outline: 'none'
        }}
        onMouseEnter={(e) => {
          e.target.style.backgroundColor = 'rgba(217, 119, 6, 0.1)';
          e.target.style.transform = 'scale(1.05)';
        }}
        onMouseLeave={(e) => {
          e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
          e.target.style.transform = 'scale(1)';
        }}
        title={isCollapsed ? 'Expand Toolbox Panel' : 'Collapse Toolbox Panel'}
      >
        {isCollapsed ? '▶' : '◀'}
      </button>
    </div>
  );
};

// Main Section Accordion Component
const AccordionSection = ({ title, icon, isOpen, onToggle, children }) => {
  return (
    <div style={{
      borderBottom: '1px solid #e5e5e5'
    }}>
      {/* Main Section Title */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          backgroundColor: isOpen ? '#fef3e7' : 'transparent',
          cursor: 'pointer',
          transition: 'background-color 0.2s ease',
          borderLeft: isOpen ? '4px solid #d97706' : '4px solid transparent'
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flex: 1
        }}>
          <span style={{ color: isOpen ? '#d97706' : '#666' }}>
            {icon}
          </span>
          <div style={{
            fontSize: '14px',
            fontWeight: '600',
            color: '#333'
          }}>
            {title}
          </div>
        </div>

        <span style={{
          fontSize: '12px',
          color: '#666',
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.3s ease'
        }}>
          ▼
        </span>
      </div>

      {/* Main Section Content */}
      <div style={{
        maxHeight: isOpen ? '2000px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 0.4s ease-in-out',
        backgroundColor: '#fafbff'
      }}>
        {children}
      </div>
    </div>
  );
};

// Sub-Module Accordion Component
const SubModuleAccordion = ({ title, icon, isOpen, onToggle, children }) => {
  return (
    <div style={{
      borderBottom: '1px solid #e0e7ff'
    }}>
      {/* Sub-Module Title */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 20px 12px 36px',
          backgroundColor: isOpen ? '#ffffff' : 'transparent',
          cursor: 'pointer',
          transition: 'background-color 0.2s ease',
          borderLeft: isOpen ? '3px solid #d97706' : '3px solid transparent'
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flex: 1
        }}>
          <span style={{ color: isOpen ? '#d97706' : '#666' }}>
            {icon}
          </span>
          <span style={{
            fontSize: '13px',
            fontWeight: '500',
            color: '#374151'
          }}>
            {title}
          </span>
        </div>

        <span style={{
          fontSize: '10px',
          color: '#999',
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.3s ease'
        }}>
          ▼
        </span>
      </div>

      {/* Sub-Module Content */}
      <div style={{
        maxHeight: isOpen ? '1500px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 0.4s ease-in-out'
      }}>
        <div style={{
          padding: isOpen ? '16px 20px 16px 36px' : '0 20px 0 36px',
          opacity: isOpen ? 1 : 0,
          transition: 'opacity 0.3s ease, padding 0.3s ease'
        }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default ToolboxPanel;