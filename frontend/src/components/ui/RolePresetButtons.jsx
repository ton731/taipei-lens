import React from 'react';

const RolePresetButtons = ({ onPresetSelect, moduleType, currentWeights }) => {
  // Define role presets based on Weight Scenario Table from PDF document
  const getRolePresets = () => {
    switch (moduleType) {
      case 'roadGreening':
        return [
          {
            id: 'environmental_priority',
            name: 'Environmental Protection Bureau',
            description: 'Prioritize areas with most severe thermal stress',
            weights: { thermal_stress: 0.50, greening_potential: 0.30, population_benefit: 0.20 }
          },
          {
            id: 'social_equity',
            name: 'Social Affairs Bureau',
            description: 'Prioritize high population benefit areas',
            weights: { thermal_stress: 0.20, greening_potential: 0.30, population_benefit: 0.50 }
          },
          {
            id: 'investment_efficiency',
            name: 'Urban Development Bureau',
            description: 'Balance greening potential and thermal stress',
            weights: { thermal_stress: 0.30, greening_potential: 0.40, population_benefit: 0.30 }
          },
          {
            id: 'balanced_development',
            name: 'Municipal Integration',
            description: 'Equal weight for all three dimensions',
            weights: { thermal_stress: 0.33, greening_potential: 0.33, population_benefit: 0.34 }
          }
        ];
      
      case 'seismicStrengthening':
        return [
          {
            id: 'structural_priority',
            name: 'Public Works Bureau',
            description: 'Prioritize retrofitting most vulnerable buildings',
            weights: { building_vulnerability: 0.50, site_amplification: 0.30, population_exposure: 0.20 }
          },
          {
            id: 'life_safety_priority',
            name: 'Civil Affairs Bureau/Fire Department',
            description: 'Protect areas with highest population exposure',
            weights: { building_vulnerability: 0.25, site_amplification: 0.15, population_exposure: 0.60 }
          },
          {
            id: 'comprehensive_risk',
            name: 'Disaster Prevention Office',
            description: 'Balance structural and site risks',
            weights: { building_vulnerability: 0.35, site_amplification: 0.35, population_exposure: 0.30 }
          },
          {
            id: 'scientific_assessment',
            name: 'Academic Institution',
            description: 'Equal weight for all three factors',
            weights: { building_vulnerability: 0.33, site_amplification: 0.33, population_exposure: 0.34 }
          }
        ];
      
      case 'parkSiting':
        return [
          {
            id: 'fill_service_gap',
            name: 'Public Works Bureau',
            description: 'Prioritize areas lacking park services',
            weights: { green_space_service_gap: 0.50, population_demand: 0.25, social_equity: 0.10, environmental_stress: 0.15 }
          },
          {
            id: 'climate_adaptation',
            name: 'Environmental Protection Bureau',
            description: 'Prioritize heat island and low vegetation areas',
            weights: { green_space_service_gap: 0.20, population_demand: 0.20, social_equity: 0.10, environmental_stress: 0.50 }
          },
          {
            id: 'social_justice',
            name: 'Social Affairs Bureau',
            description: 'Prioritize vulnerable populations',
            weights: { green_space_service_gap: 0.20, population_demand: 0.20, social_equity: 0.50, environmental_stress: 0.10 }
          },
          {
            id: 'demand_driven',
            name: 'Urban Development Bureau',
            description: 'Allocate resources by population demand',
            weights: { green_space_service_gap: 0.25, population_demand: 0.40, social_equity: 0.15, environmental_stress: 0.20 }
          },
          {
            id: 'balanced_development',
            name: 'Municipal Integration',
            description: 'Equal weight for all four dimensions',
            weights: { green_space_service_gap: 0.25, population_demand: 0.25, social_equity: 0.25, environmental_stress: 0.25 }
          }
        ];
      
      case 'urbanRenewal':
        return [
          {
            id: 'disaster_prevention',
            name: 'Disaster Prevention',
            description: 'Prioritize building vulnerability reduction',
            weights: { building_vulnerability: 0.50, environmental_quality: 0.20, population_exposure: 0.30 }
          },
          {
            id: 'quality_of_life',
            name: 'Quality of Life',
            description: 'Focus on improving environmental quality',
            weights: { building_vulnerability: 0.25, environmental_quality: 0.50, population_exposure: 0.25 }
          },
          {
            id: 'comprehensive_assessment',
            name: 'Comprehensive Assessment',
            description: 'Equal weight for all three dimensions',
            weights: { building_vulnerability: 0.33, environmental_quality: 0.33, population_exposure: 0.34 }
          }
        ];
      
      default:
        return [];
    }
  };

  const rolePresets = getRolePresets();

  const handlePresetClick = (preset) => {
    onPresetSelect(preset.weights);
  };

  // 檢查當前權重是否與某個預設相符
  const isPresetActive = (presetWeights) => {
    if (!currentWeights) return false;
    
    const keys = Object.keys(presetWeights);
    return keys.every(key => 
      Math.abs(currentWeights[key] - presetWeights[key]) < 0.01
    );
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{
        fontSize: '13px',
        fontWeight: '600',
        color: '#374151',
        marginBottom: '8px'
      }}>
        Scenario-based Presets
      </div>
      
      <div style={{
        display: 'flex',
        overflowX: 'auto',
        gap: '8px',
        marginBottom: '12px',
        paddingBottom: '4px',
        scrollbarWidth: 'thin',
        scrollbarColor: '#d1d5db #f3f4f6'
      }}>
        {rolePresets.map((preset) => (
          <button
            key={preset.id}
            onClick={() => handlePresetClick(preset)}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              border: isPresetActive(preset.weights) 
                ? '2px solid #d97706' 
                : '1px solid #e5e5e5',
              backgroundColor: isPresetActive(preset.weights) 
                ? 'rgba(217, 119, 6, 0.1)' 
                : '#ffffff',
              cursor: 'pointer',
              textAlign: 'center',
              fontSize: '11px',
              fontWeight: '500',
              color: isPresetActive(preset.weights) ? '#d97706' : '#374151',
              transition: 'all 0.2s ease',
              minHeight: 'auto',
              minWidth: '120px',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '2px',
              outline: 'none'
            }}
            onMouseEnter={(e) => {
              if (!isPresetActive(preset.weights)) {
                e.target.style.backgroundColor = '#f9fafb';
                e.target.style.borderColor = '#d1d5db';
              }
            }}
            onMouseLeave={(e) => {
              if (!isPresetActive(preset.weights)) {
                e.target.style.backgroundColor = '#ffffff';
                e.target.style.borderColor = '#e5e5e5';
              }
            }}
            title={preset.description}
          >
            <span>{preset.name}</span>
          </button>
        ))}
      </div>
      
      <div style={{
        fontSize: '11px',
        color: '#6b7280',
        textAlign: 'center',
        fontStyle: 'italic'
      }}>
        Select a scenario preset or manually adjust weights
      </div>
    </div>
  );
};

export default RolePresetButtons;