#!/usr/bin/env python3
"""
Incremental Dynamic Analysis (IDA) Engine
Handles time-history analysis with ground motion scaling
"""

import numpy as np
import openseespy.opensees as ops
import eqsig
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class IDAEngine:
    """
    Incremental Dynamic Analysis Engine for OpenSeesPy
    """

    def __init__(self, structural_model, gm_processor, analysis_config: Dict):
        """
        Initialize the IDA Engine

        Args:
            structural_model: Instance of StickModel
            gm_processor: Instance of GroundMotionProcessor
            analysis_config (Dict): Analysis configuration parameters
        """
        self.structural_model = structural_model
        self.gm_processor = gm_processor
        self.analysis_config = analysis_config

        # Extract analysis parameters - now using PGA as IM
        # Support both new (pga_targets) and legacy (sa_targets, im_levels_g) parameter names
        self.im_levels = analysis_config.get('pga_targets',
                                           analysis_config.get('im_levels_g',
                                                              analysis_config.get('sa_targets', [])))
        self.damage_states = analysis_config.get('damage_states', {})
        self.max_drift_ratio = analysis_config.get('max_drift_ratio', 0.10)
        self.convergence_tolerance = analysis_config.get('convergence_tolerance', 1e-6)
        self.max_iterations = analysis_config.get('max_iterations', 100)

        # Results storage
        self.ida_results = []
        self.analysis_summary = {}

        # Get fundamental period for spectral acceleration calculation
        self._get_fundamental_period()

    def _get_fundamental_period(self):
        """Get or estimate the fundamental period"""
        if self.structural_model.fundamental_period is not None:
            self.T1 = self.structural_model.fundamental_period
        else:
            # Try to compute it
            success, T1 = self.structural_model.perform_eigenvalue_analysis()
            if success:
                self.T1 = T1
            else:
                # Use default estimate
                self.T1 = 0.1 * self.structural_model.num_stories
                logger.warning(f"Using estimated fundamental period: T1 = {self.T1:.4f} sec")

    def calculate_pga(self, ground_motion: np.ndarray, dt: float, damping: float = 0.05) -> float:
        """
        Calculate Peak Ground Acceleration (PGA) = Sa(T=0)

        Args:
            ground_motion (np.ndarray): Ground motion acceleration time series (cm/s²)
            dt (float): Time step
            damping (float): Damping ratio (default: 0.05)

        Returns:
            float: PGA in g units
        """
        # Convert to g units for eqsig
        accel_g = [acc/980.665 for acc in ground_motion]
        record = eqsig.AccSignal(accel_g, dt)

        # Calculate response spectrum with very small period to approximate T=0
        periods = [0.001]  # Very small period to approximate T=0
        record.generate_response_spectrum(response_times=periods)

        # Return PGA (which is Sa at T≈0)
        pga_g = record.s_a[0]
        return pga_g

    def calculate_spectral_acceleration(self, ground_motion: np.ndarray, dt: float, period: float, damping: float = 0.05) -> float:
        """
        Calculate spectral acceleration for a given period
        WARNING: Error handling removed for debugging

        Args:
            ground_motion (np.ndarray): Ground motion acceleration time series (cm/s²)
            dt (float): Time step
            period (float): Period of interest (seconds)
            damping (float): Damping ratio (default: 0.05)

        Returns:
            float: Spectral acceleration in g units
        """
        # Keep acceleration in cm/s² (consistent with kgf-cm-sec system)
        accel_cms2 = ground_motion

        # Response calculation using Duhamel's integral (simplified)
        n_points = len(accel_cms2)
        time_vec = np.arange(n_points) * dt

        # Initialize response
        disp = np.zeros(n_points)
        vel = np.zeros(n_points)
        acc = np.zeros(n_points)

        # Time integration (Newmark's method)
        gamma = 0.5
        beta = 0.25


        periods = np.arange(0.1, 50.0, 0.1)

        accel_g = [acc/1000/9.80665 for acc in accel_cms2]
        record_FN = eqsig.AccSignal(accel_g, dt)

        record_FN.generate_response_spectrum(response_times=periods)

        # find the nearest period
        nearest_period_index = np.argmin(np.abs(periods - period))
        sa_g = record_FN.s_a[nearest_period_index]

        return sa_g

    def scale_ground_motion(self, ground_motion: np.ndarray, dt: float, target_pga: float) -> Tuple[np.ndarray, float]:
        """
        Scale ground motion to target PGA (Peak Ground Acceleration)
        WARNING: Error handling removed for debugging

        Args:
            ground_motion (np.ndarray): Original ground motion
            dt (float): Time step
            target_pga (float): Target PGA in g units

        Returns:
            Tuple[np.ndarray, float]: (Scaled ground motion, Scale factor)
        """
        # Calculate current PGA
        current_pga = self.calculate_pga(ground_motion, dt)

        if current_pga <= 0:
            logger.warning("Invalid current PGA, using direct PGA calculation")
            # Direct PGA calculation as fallback
            current_pga = np.max(np.abs(ground_motion)) / 980.665  # Convert from cm/s² to g

        # Calculate scale factor
        scale_factor = target_pga / current_pga

        # Scale the ground motion
        scaled_gm = ground_motion * scale_factor

        return scaled_gm, scale_factor

    def setup_time_history_analysis(self, dt: float, n_steps: int):
        """
        Setup OpenSees for time history analysis
        WARNING: Error handling removed for debugging

        Args:
            dt (float): Time step for analysis
            n_steps (int): Number of analysis steps
        """
        # Clear previous analysis
        ops.wipeAnalysis()

        # Constraints
        ops.constraints('Plain')

        # Numberer
        ops.numberer('RCM')

        # System of equations
        ops.system('BandGeneral')

        # Convergence test
        ops.test('NormDispIncr', self.convergence_tolerance, self.max_iterations)

        # Solution algorithm
        ops.algorithm('Newton')

        # Integrator (Newmark-beta method)
        ops.integrator('Newmark', 0.5, 0.25)

        # Analysis type
        ops.analysis('Transient')

        # Rayleigh damping
        if hasattr(self.structural_model, 'damping_ratio'):
            # Calculate damping coefficients
            omega1 = 2 * np.pi / self.T1
            omega2 = omega1 * 3  # Assume second mode is 3x first mode

            damping_ratio = self.structural_model.damping_ratio
            a0 = damping_ratio * 2 * omega1 * omega2 / (omega1 + omega2)
            a1 = damping_ratio * 2 / (omega1 + omega2)

            ops.rayleigh(a0, a1, 0.0, 0.0)

    def run_single_analysis(self, gm_id: str, target_pga: float, component: str = 'FN') -> Optional[Dict]:
            """
            Run single time history analysis for a given GM and intensity

            Args:
                gm_id (str): Ground motion ID
                target_pga (float): Target PGA in g
                component (str): Ground motion component ('FN' or 'FP')

            Returns:
                Optional[Dict]: Analysis results or None if failed
            """
        # try:
            # Clear previous analysis and rebuild model for each analysis
            ops.wipe()

            # Rebuild the structural model
            if not self.structural_model.build_model():
                logger.error(f"Failed to rebuild model for {gm_id} at PGA={target_pga:.3f}g")
                return None

            # Load ground motion
            ground_motion = self.gm_processor.load_ground_motion(gm_id, component)
            dt = self.gm_processor.dt

            # Scale ground motion to target PGA
            scaled_gm, scale_factor = self.scale_ground_motion(ground_motion, dt, target_pga)

            # Keep acceleration in cm/s² (consistent with kgf-cm-sec system)
            accel_cms2 = scaled_gm  # Already in cm/s²

            # Setup analysis
            n_steps = len(accel_cms2)
            self.setup_time_history_analysis(dt, n_steps)

            gm_index = int(gm_id.replace("EQ", ""))
            pga_level_index = int(target_pga * 100)
            ts_tag = int(f"{gm_index}{pga_level_index}")
            time_vec = np.arange(n_steps) * dt
            # Create ground motion time series and load pattern
            # timeSeries('Path', tag, '-dt', dt=0.0, '-values', *values, '-time', *time, '-filePath', filePath='', '-fileTime', fileTime='', '-factor', factor=1.0, '-startTime', startTime=0.0, '-useLast', '-prependZero')
            ops.timeSeries('Path', ts_tag, '-dt', dt, '-values', *accel_cms2, '-time', *time_vec)

            ops.pattern('UniformExcitation',  ts_tag,   1,  '-accel', ts_tag)

            # Setup recorders for displacement
            displacement_file = f"temp_displacement_{gm_id}.out"
            ops.recorder('Node', '-file', displacement_file, '-time',
                        '-node', *self.structural_model.node_tags[1:],  # Exclude base node
                        '-dof', 1, 'disp')

            # Run analysis
            analysis_success = True
            max_displacement = 0.0
            max_idr = 0.0

            for step in range(n_steps):
                if ops.analyze(1, dt) != 0:
                    logger.warning(f"Analysis convergence failed at step {step} for {gm_id} at PGA={target_pga:.3f}g")
                    analysis_success = False
                    break

                # Check current displacements
                current_disps = []
                for node_tag in self.structural_model.node_tags[1:]:  # Exclude base
                    disp = ops.nodeDisp(node_tag, 1)
                    current_disps.append(disp)

                # Calculate current IDR
                current_idr = self._calculate_max_idr(current_disps)
                max_idr = max(max_idr, current_idr)
                max_displacement = max(max_displacement, max(abs(d) for d in current_disps))

                # Check for collapse (excessive drift)
                if max_idr > self.max_drift_ratio:
                    logger.info(f"Collapse detected for {gm_id} at PGA={target_pga:.3f}g (IDR={max_idr:.4f})")
                    analysis_success = False
                    break
            # if gm_id == "EQ160":
            #     assert False, "Stop here"
            # Clean up
            ops.remove('recorders')
            ops.remove('loadPattern', ts_tag)
            ops.remove('timeSeries', ts_tag)

            # Remove temp file
            Path(displacement_file).unlink(missing_ok=True)

            # Return results
            result = {
                'gm_id': gm_id,
                'pga_target': target_pga,
                'pga_actual': target_pga,  # After scaling
                'scale_factor': scale_factor,
                'max_displacement': max_displacement,
                'max_idr': max_idr,
                'analysis_success': analysis_success,
                'collapse': max_idr > self.max_drift_ratio or not analysis_success,
                'component': component
            }

            return result

        # except Exception as e:
        #     logger.error(f"Single analysis failed for {gm_id} at PGA={target_pga:.3f}g: {e}")
        #     return None

    def _calculate_max_idr(self, displacements: List[float]) -> float:
        """
        Calculate maximum interstory drift ratio using actual story heights

        Args:
            displacements (List[float]): Story displacements in cm

        Returns:
            float: Maximum interstory drift ratio
        """
        if not displacements:
            return 0.0

        max_idr = 0.0

        # Get story heights from structural model
        story_heights = []

        # 驗證 model_properties 的類型和內容
        if not hasattr(self.structural_model, 'model_properties'):
            logger.error("structural_model missing 'model_properties' attribute")
            # 使用預設值
            story_heights = [300.0] * len(displacements)
        elif not isinstance(self.structural_model.model_properties, list):
            logger.error(f"model_properties is not a list: {type(self.structural_model.model_properties)}")
            # 使用預設值
            story_heights = [300.0] * len(displacements)
        else:
            for i, props in enumerate(self.structural_model.model_properties):
                if isinstance(props, dict):
                    height = props.get('story_height', 300.0)  # cm
                else:
                    logger.warning(f"Story {i} properties is not a dict: {type(props)}, using default height")
                    height = 300.0  # Default height
                story_heights.append(height)

        for i in range(len(displacements)):
            if i == 0:
                # First story relative to ground
                relative_disp = displacements[i]  # cm
            else:
                # Other stories relative to story below
                relative_disp = displacements[i] - displacements[i-1]  # cm

            # Get story height (ensure we don't exceed available heights)
            story_height = story_heights[min(i, len(story_heights)-1)]  # cm

            # Calculate IDR (dimensionless)
            idr = abs(relative_disp) / story_height
            max_idr = max(max_idr, idr)

            logger.debug(f"Story {i+1}: disp={displacements[i]:.6f}cm, rel_disp={relative_disp:.6f}cm, height={story_height:.1f}cm, IDR={idr:.6f}")

        logger.debug(f"Max IDR calculated: {max_idr:.6f}")
        return max_idr

    def run_ida_for_gm(self, gm_id: str) -> List[Dict]:
        """
        Run IDA for a single ground motion record

        Args:
            gm_id (str): Ground motion ID

        Returns:
            List[Dict]: List of analysis results for different intensity levels
        """
        logger.info(f"Running IDA for ground motion: {gm_id}")

        results = []
        collapsed = False

        for pga_level in self.im_levels:
            if collapsed:
                # Skip further analysis if already collapsed
                break

            result = self.run_single_analysis(gm_id, pga_level)

            if result is not None:
                results.append(result)

                if result['collapse']:
                    collapsed = True
                    logger.info(f"Collapse reached for {gm_id} at PGA={pga_level:.3f}g")
            else:
                logger.warning(f"Analysis failed for {gm_id} at PGA={pga_level:.3f}g")

        return results

    def run_full_ida(self) -> pd.DataFrame:
        """
        Run IDA for all ground motions

        Returns:
            pd.DataFrame: Complete IDA results
        """
        logger.info("Starting full IDA analysis...")

        all_results = []
        gm_ids = self.gm_processor.get_available_gm_ids()

        start_time = time.time()

        for i, gm_id in enumerate(gm_ids):
            logger.info(f"Processing GM {i+1}/{len(gm_ids)}: {gm_id}")

            # Run IDA for this ground motion
            gm_results = self.run_ida_for_gm(gm_id)
            all_results.extend(gm_results)

            # Progress update
            if (i + 1) % 5 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Completed {i+1}/{len(gm_ids)} ground motions "
                          f"({elapsed/60:.1f} minutes elapsed)")

        # Convert to DataFrame
        df_results = pd.DataFrame(all_results)
        self.ida_results = df_results

        # Generate summary
        self._generate_analysis_summary()

        elapsed_total = time.time() - start_time
        logger.info(f"IDA analysis completed in {elapsed_total/60:.1f} minutes")
        logger.info(f"Total analyses: {len(all_results)}")

        return df_results

    def _generate_analysis_summary(self):
        """Generate analysis summary statistics"""
        if self.ida_results.empty:
            return

        df = self.ida_results

        self.analysis_summary = {
            'total_analyses': len(df),
            'successful_analyses': len(df[df['analysis_success'] == True]),
            'collapsed_analyses': len(df[df['collapse'] == True]),
            'gm_count': df['gm_id'].nunique(),
            'pga_levels_analyzed': df['pga_target'].nunique(),
            'max_pga_without_collapse': df[df['collapse'] == False]['pga_target'].max() if len(df[df['collapse'] == False]) > 0 else 0,
            'min_pga_with_collapse': df[df['collapse'] == True]['pga_target'].min() if len(df[df['collapse'] == True]) > 0 else float('inf'),
            'mean_max_idr': df['max_idr'].mean(),
            'std_max_idr': df['max_idr'].std()
        }

    def get_analysis_summary(self) -> Dict:
        """Get analysis summary"""
        return self.analysis_summary

    def save_results(self, output_file: str):
        """
        Save IDA results to CSV file

        Args:
            output_file (str): Output file path
        """
        if not self.ida_results.empty:
            self.ida_results.to_csv(output_file, index=False)
            logger.info(f"IDA results saved to: {output_file}")
        else:
            logger.warning("No results to save")


def main():
    """Test the IDA engine with a simple example"""
    # This would require the other modules to be properly imported
    print("IDA Engine module loaded successfully")
    print("To test, use the main generate_fragility_curves function")


if __name__ == "__main__":
    main()