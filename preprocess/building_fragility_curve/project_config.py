#!/usr/bin/env python3
"""
Project Configuration and Directory Management
Handles creation and management of output directories
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ProjectConfig:
    """
    Manages project configuration and directory structure
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize project configuration

        Args:
            base_dir (str, optional): Base directory for the project
        """
        if base_dir is None:
            self.base_dir = Path.cwd()
        else:
            self.base_dir = Path(base_dir)

        self.results_dir = self.base_dir / "results"
        self.ground_motions_dir = self.base_dir / "ground_motions"
        self.tests_dir = self.base_dir / "tests"
        self.src_dir = self.base_dir / "src"
        self.docs_dir = self.base_dir / "docs"

    def setup_directories(self, building_id: Optional[str] = None) -> Dict[str, Path]:
        """
        Create all necessary directories for the project

        Args:
            building_id (str, optional): Specific building ID for results

        Returns:
            Dict[str, Path]: Dictionary of created directory paths
        """
        directories = {
            'base': self.base_dir,
            'results': self.results_dir,
            'ground_motions': self.ground_motions_dir,
            'tests': self.tests_dir,
            'src': self.src_dir,
            'docs': self.docs_dir
        }

        # Create building-specific results directory if building_id is provided
        if building_id:
            building_results_dir = self.results_dir / building_id
            directories['building_results'] = building_results_dir

        # Create all directories
        for name, path in directories.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Directory ensured: {path}")
            except Exception as e:
                logger.error(f"Failed to create directory {path}: {e}")
                raise

        return directories

    def get_building_output_path(self, building_id: str) -> Path:
        """
        Get the output path for a specific building

        Args:
            building_id (str): Building identifier

        Returns:
            Path: Path to building-specific output directory
        """
        building_path = self.results_dir / building_id
        building_path.mkdir(parents=True, exist_ok=True)
        return building_path

    def get_output_file_path(self, building_id: str, filename: str) -> Path:
        """
        Get full path for an output file

        Args:
            building_id (str): Building identifier
            filename (str): Output filename

        Returns:
            Path: Full path to output file
        """
        building_dir = self.get_building_output_path(building_id)
        return building_dir / filename

    def validate_inputs(self, gm_directory: str, gm_list_file: str) -> bool:
        """
        Validate that required input files/directories exist

        Args:
            gm_directory (str): Ground motion directory path
            gm_list_file (str): Ground motion list file path

        Returns:
            bool: True if all inputs are valid
        """
        gm_dir_path = Path(gm_directory)
        gm_list_path = Path(gm_list_file)

        # Check ground motion directory
        if not gm_dir_path.exists():
            logger.error(f"Ground motion directory not found: {gm_directory}")
            return False

        if not gm_dir_path.is_dir():
            logger.error(f"Ground motion path is not a directory: {gm_directory}")
            return False

        # Check GM list file
        if not gm_list_path.exists():
            logger.warning(f"Ground motion list file not found: {gm_list_file}")
            # This might be created automatically, so just warn

        logger.info("Input validation successful")
        return True

    def get_area_scale_standards(self) -> Dict:
        """
        Get standard representative areas for building size classifications

        Returns:
            Dict: Standard areas for S/M/L classifications
        """
        return {
            'S': {
                'representative_area': 100.0,  # m² - 代表小型建築 (< 150 m²)
                'threshold_min': 0.0,
                'threshold_max': 150.0,
                'description': '小型建築物 (< 150 m²)'
            },
            'M': {
                'representative_area': 300.0,  # m² - 代表中型建築 (150-500 m²)
                'threshold_min': 150.0,
                'threshold_max': 500.0,
                'description': '中型建築物 (150-500 m²)'
            },
            'L': {
                'representative_area': 700.0,  # m² - 代表大型建築 (> 500 m²)
                'threshold_min': 500.0,
                'threshold_max': float('inf'),
                'description': '大型建築物 (> 500 m²)'
            }
        }

    def get_default_analysis_config(self) -> Dict:
        """
        Get default analysis configuration

        Returns:
            Dict: Default analysis configuration
        """
        return {
            "pga_targets": [
                0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4,
                0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                1.2, 1.4, 1.6, 1.8, 2.0
            ],
            # 支援舊的參數名稱以保持向後相容
            "im_levels_g": [
                0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4,
                0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                1.2, 1.4, 1.6, 1.8, 2.0
            ],
            "damage_states": {
                'DS0_Slight_NSD': 0.002,    # 0.2%
                'DS1_Slight_SD': 0.005,     # 0.5%
                'DS2_Moderate_SD': 0.015,   # 1.5%
                'DS3_Severe_SD': 0.025,     # 2.5%
                'DS4_Collapse': 0.050       # 5.0%
            },
            "max_drift_ratio": 0.10,  # 10% - analysis stops if exceeded
            "convergence_tolerance": 1e-6,
            "max_iterations": 100
        }

    def create_project_summary(self) -> str:
        """
        Create a summary of the project configuration

        Returns:
            str: Project configuration summary
        """
        summary = f"""
Fragility Curve Analysis Project Configuration
==============================================

Base Directory: {self.base_dir}
Results Directory: {self.results_dir}
Ground Motions Directory: {self.ground_motions_dir}
Source Directory: {self.src_dir}
Tests Directory: {self.tests_dir}
Documentation Directory: {self.docs_dir}

Default Analysis Configuration:
- PGA Levels: {len(self.get_default_analysis_config()['pga_targets'])} levels
- Damage States: {len(self.get_default_analysis_config()['damage_states'])} states
- Max Drift Ratio: {self.get_default_analysis_config()['max_drift_ratio']:.1%}
"""
        return summary


def main():
    """Test the project configuration"""
    # Initialize configuration
    config = ProjectConfig()

    # Setup directories
    dirs = config.setup_directories("Test_Building_RC5F")
    print("Created directories:")
    for name, path in dirs.items():
        print(f"  {name}: {path}")

    # Test validation
    is_valid = config.validate_inputs("./ground_motions", "./ground_motions/GM_List.csv")
    print(f"\nInput validation: {'PASSED' if is_valid else 'FAILED'}")

    # Print summary
    print(config.create_project_summary())

    # Test output path generation
    output_file = config.get_output_file_path("Test_Building_RC5F", "fragility_curve.png")
    print(f"\nExample output file path: {output_file}")


if __name__ == "__main__":
    main()