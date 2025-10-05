#!/usr/bin/env python3
"""
Ground Motion Data Processing Module for Fragility Curve Analysis
Handles scanning, loading, and validation of ground motion records
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroundMotionProcessor:
    """
    Class for handling ground motion data processing
    """

    def __init__(self, gm_directory: str, gm_list_file: str = None, dt: float = 0.05):
        """
        Initialize the Ground Motion Processor

        Args:
            gm_directory (str): Path to directory containing ground motion files
            gm_list_file (str): Path to ground motion list file (optional)
            dt (float): Time step for ground motion records (default: 0.05 sec)
        """
        self.gm_directory = Path(gm_directory)
        self.gm_list_file = Path(gm_list_file) if gm_list_file else None
        self.dt = dt
        self.gm_inventory = {}
        self._validate_directory()

    def _validate_directory(self):
        """Validate that the ground motion directory exists and contains data"""
        if not self.gm_directory.exists():
            raise FileNotFoundError(f"Ground motion directory not found: {self.gm_directory}")

        if not self.gm_directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.gm_directory}")

        logger.info(f"Ground motion directory validated: {self.gm_directory}")

    def scan_ground_motions(self) -> Dict[str, Dict]:
        """
        Scan the ground motion directory and build inventory

        Returns:
            Dict[str, Dict]: Dictionary with GM IDs and their file information
        """
        logger.info("Scanning ground motion directory...")

        # Find all subdirectories (should be EQ### format)
        eq_dirs = [d for d in self.gm_directory.iterdir() if d.is_dir()]

        self.gm_inventory = {}

        for eq_dir in sorted(eq_dirs):
            eq_id = eq_dir.name

            # Look for FN and FP components
            fn_file = eq_dir / f"{eq_id}_FN.txt"
            fp_file = eq_dir / f"{eq_id}_FP.txt"

            if fn_file.exists() and fp_file.exists():
                # Validate file contents
                fn_valid = self._validate_gm_file(fn_file)
                fp_valid = self._validate_gm_file(fp_file)

                if fn_valid and fp_valid:
                    self.gm_inventory[eq_id] = {
                        'fn_file': str(fn_file),
                        'fp_file': str(fp_file),
                        'dt': self.dt,
                        'validated': True
                    }
                else:
                    logger.warning(f"Invalid ground motion files in {eq_dir}")
            else:
                logger.warning(f"Missing FN or FP files in {eq_dir}")

        logger.info(f"Found {len(self.gm_inventory)} valid ground motion records")
        return self.gm_inventory

    def _validate_gm_file(self, file_path: Path) -> bool:
        """
        Validate a single ground motion file

        Args:
            file_path (Path): Path to ground motion file

        Returns:
            bool: True if file is valid
        """
        try:
            # Check if file exists and is readable
            if not file_path.exists():
                return False

            # Try to read first few lines
            with open(file_path, 'r') as f:
                lines = f.readlines()[:10]

            # Check if lines contain numeric data
            for line in lines:
                try:
                    float(line.strip())
                except ValueError:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            return False

    def load_ground_motion(self, gm_id: str, component: str = 'FN') -> np.ndarray:
        """
        Load a specific ground motion record

        Args:
            gm_id (str): Ground motion ID (e.g., 'EQ125')
            component (str): Component to load ('FN' or 'FP')

        Returns:
            np.ndarray: Ground motion acceleration array
        """
        if gm_id not in self.gm_inventory:
            raise ValueError(f"Ground motion {gm_id} not found in inventory")

        if component not in ['FN', 'FP']:
            raise ValueError("Component must be 'FN' or 'FP'")

        file_key = f"{component.lower()}_file"
        file_path = self.gm_inventory[gm_id][file_key]

        try:
            # Load acceleration data
            acceleration = np.loadtxt(file_path)
            logger.debug(f"Loaded {gm_id}_{component}: {len(acceleration)} points")
            return acceleration

        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            raise

    def get_ground_motion_info(self, gm_id: str) -> Dict:
        """
        Get information about a specific ground motion

        Args:
            gm_id (str): Ground motion ID

        Returns:
            Dict: Ground motion information
        """
        if gm_id not in self.gm_inventory:
            raise ValueError(f"Ground motion {gm_id} not found")

        info = self.gm_inventory[gm_id].copy()

        # Add computed properties
        fn_accel = self.load_ground_motion(gm_id, 'FN')
        info.update({
            'num_points': len(fn_accel),
            'duration': len(fn_accel) * self.dt,
            'max_acceleration_fn': np.max(np.abs(fn_accel)),
            'dt': self.dt
        })

        return info

    def create_gm_list_file(self, output_path: str) -> str:
        """
        Create a ground motion list file compatible with the main analysis

        Args:
            output_path (str): Path where to save the GM list file

        Returns:
            str: Path to created GM list file
        """
        if not self.gm_inventory:
            self.scan_ground_motions()

        gm_list = []

        for gm_id, info in self.gm_inventory.items():
            gm_list.append({
                'GM_ID': gm_id,
                'FN_File': info['fn_file'],
                'FP_File': info['fp_file'],
                'dt': info['dt']
            })

        # Create DataFrame and save
        df = pd.DataFrame(gm_list)
        df.to_csv(output_path, index=False)

        logger.info(f"Ground motion list saved to: {output_path}")
        return output_path

    def get_available_gm_ids(self) -> List[str]:
        """
        Get list of available ground motion IDs

        Returns:
            List[str]: List of GM IDs
        """
        if not self.gm_inventory:
            self.scan_ground_motions()

        return list(self.gm_inventory.keys())


def main():
    """Test the ground motion processor"""
    # Initialize processor
    gm_processor = GroundMotionProcessor("./ground_motions")

    # Scan ground motions
    inventory = gm_processor.scan_ground_motions()
    print(f"Found {len(inventory)} ground motion records")

    # Test loading a few records
    available_gms = gm_processor.get_available_gm_ids()[:3]  # First 3 GMs

    for gm_id in available_gms:
        info = gm_processor.get_ground_motion_info(gm_id)
        print(f"{gm_id}: {info['num_points']} points, "
              f"duration={info['duration']:.2f}s, "
              f"max_accel={info['max_acceleration_fn']:.2f}")

    # Create GM list file
    list_file = gm_processor.create_gm_list_file("./ground_motions/GM_List.csv")
    print(f"GM list created: {list_file}")

    # Validate all GMs
    print(f"Validation complete: {len(inventory)} GMs are valid")


if __name__ == "__main__":
    main()