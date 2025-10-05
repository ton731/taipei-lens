#!/usr/bin/env python3
"""
Structural Modeling Module for OpenSeesPy Fragility Analysis
Implements multi-story stick model with nonlinear elements
"""

import numpy as np
import openseespy.opensees as ops
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class StickModel:
    """
    Multi-story stick model builder for OpenSeesPy
    """

    def __init__(self, model_properties: List[Dict], damping_ratio: float = 0.05):
        """
        Initialize the stick model

        Args:
            model_properties (List[Dict]): List of story properties
                Each dict should contain: story, mass, k, Fy, alpha
            damping_ratio (float): Structural damping ratio (default: 0.05)
        """
        self.model_properties = model_properties
        self.damping_ratio = damping_ratio
        self.num_stories = len(model_properties)
        self.node_tags = []
        self.element_tags = []
        self.fundamental_period = None

        # Validate input
        self._validate_model_properties()

    def _validate_model_properties(self):
        """Validate the input model properties"""
        required_keys = ['story', 'mass', 'k', 'Fy', 'alpha']

        for i, props in enumerate(self.model_properties):
            # Check required keys
            for key in required_keys:
                if key not in props:
                    raise ValueError(f"Missing key '{key}' in story {i+1} properties")

            # Check data types and ranges
            if not isinstance(props['story'], int) or props['story'] <= 0:
                raise ValueError(f"Story number must be positive integer, got {props['story']}")

            if props['mass'] <= 0:
                raise ValueError(f"Mass must be positive, got {props['mass']} for story {props['story']}")

            if props['k'] <= 0:
                raise ValueError(f"Stiffness must be positive, got {props['k']} for story {props['story']}")

            if props['Fy'] <= 0:
                raise ValueError(f"Yield strength must be positive, got {props['Fy']} for story {props['story']}")

            if not 0 <= props['alpha'] <= 1:
                raise ValueError(f"Hardening ratio must be between 0 and 1, got {props['alpha']} for story {props['story']}")

            # Validate optional parameters
            if 'material_type' in props:
                valid_materials = ['steel', 'concrete', None]
                if props['material_type'] not in valid_materials:
                    raise ValueError(f"Material type must be one of {valid_materials}, got {props['material_type']} for story {props['story']}")

            if 'E' in props and props['E'] <= 0:
                raise ValueError(f"Elastic modulus must be positive, got {props['E']} for story {props['story']}")

            if 'story_height' in props and props['story_height'] <= 0:
                raise ValueError(f"Story height must be positive, got {props['story_height']} for story {props['story']}")

        # Check story numbering is consecutive
        story_nums = [p['story'] for p in self.model_properties]
        if story_nums != list(range(1, self.num_stories + 1)):
            raise ValueError("Story numbers must be consecutive starting from 1")

        # Set default values for optional parameters
        self._set_default_parameters()

        logger.debug(f"Model properties validation passed for {self.num_stories} stories")

    def _set_default_parameters(self):
        """Set default values for optional parameters"""
        for props in self.model_properties:
            # Set default story height
            if 'story_height' not in props:
                props['story_height'] = 300.0  # Default 300cm per story

            # Set default elastic modulus based on material type
            if 'E' not in props:
                material_type = props.get('material_type', 'concrete')
                if material_type == 'steel':
                    props['E'] = 2.0e6  # Steel: 2.0×10^6 kgf/cm²
                else:  # concrete or default
                    props['E'] = 3.6e5  # Concrete: 3.6×10^5 kgf/cm²

            # Set material_type if not specified
            if 'material_type' not in props:
                props['material_type'] = 'concrete'  # Default to concrete

        logger.debug("Default parameters set for all stories")

    def build_model(self) -> bool:
        """
        Build the OpenSees stick model

        Returns:
            bool: True if model built successfully
        """
        try:
            # Clear any existing model (ensure clean start)
            ops.wipe()

            # Model builder: 2D frame, 3 DOF per node
            ops.model('basic', '-ndm', 2, '-ndf', 3)
            logger.debug("OpenSees model initialized (2D, 3DOF)")

            # Create nodes
            self._create_nodes()

            # Apply boundary conditions
            self._apply_boundary_conditions()

            # Define materials
            self._define_materials()

            # Create elements
            self._create_elements()

            # Apply masses
            self._apply_masses()

            # Setup analysis parameters
            self._setup_analysis_parameters()

            logger.debug(f"Stick model built successfully: {self.num_stories} stories")
            return True

        except Exception as e:
            logger.error(f"Failed to build model: {e}")
            return False

    def _create_nodes(self):
        """Create nodes for the stick model with nonlinear elements"""
        self.node_tags = []

        # Ground node at origin
        ops.node(1, 0.0, 0.0)
        self.node_tags.append(1)

        # Create node pairs for each story (bottom and top nodes at same height)
        cumulative_height = 0.0
        for i, props in enumerate(self.model_properties):
            story_num = props['story']
            cumulative_height += props['story_height']  # Use individual story height

            # Bottom node of the story (even node numbers: 2, 4, 6, ...)
            bottom_node_tag = 2 * story_num
            ops.node(bottom_node_tag, 0.0, cumulative_height)
            self.node_tags.append(bottom_node_tag)

            # Top node of the story (odd node numbers: 3, 5, 7, ...)
            top_node_tag = 2 * story_num + 1
            ops.node(top_node_tag, 0.0, cumulative_height)
            self.node_tags.append(top_node_tag)

            logger.info(f"Story {story_num}: Bottom node {bottom_node_tag}, Top node {top_node_tag} at height {cumulative_height:.0f} cm")

        logger.info(f"Created {len(self.node_tags)} nodes ({self.num_stories} story pairs + ground)")
        logger.info(f"All node tags: {self.node_tags}")

    def _apply_boundary_conditions(self):
        """Apply boundary conditions for stick model with nonlinear elements"""
        # Fix ground node (all DOFs): UX=UY=RZ=0
        ops.fix(1, 1, 1, 1)

        # For each story, apply boundary conditions to both bottom and top nodes
        for i, props in enumerate(self.model_properties):
            story_num = props['story']
            bottom_node = 2 * story_num      # Bottom node (even numbers)
            top_node = 2 * story_num + 1     # Top node (odd numbers)

            # Bottom nodes: only allow UX (lateral displacement), fix UY=RZ=0
            ops.fix(bottom_node, 0, 1, 1)  # UX=free, UY=RZ=fixed

            # Top nodes: only allow UX (lateral displacement), fix UY=RZ=0
            ops.fix(top_node, 0, 1, 1)      # UX=free, UY=RZ=fixed

            logger.debug(f"Story {story_num}: Fixed nodes {bottom_node} and {top_node} (UY=RZ=0, UX=free)")

        logger.debug(f"Boundary conditions applied to {2 * self.num_stories} story nodes + ground node")

    def _define_materials(self):
        """Define materials for each story"""
        for i, props in enumerate(self.model_properties):
            mat_tag = props['story']

            # Extract material properties
            k = props['k']  # Elastic stiffness (kgf/cm)
            Fy = props['Fy']  # Yield strength (kgf)
            alpha = props['alpha']  # Post-yield stiffness ratio

            # Calculate elastic modulus and post-yield stiffness
            E = k  # For stick model, E = k
            b = alpha  # Post-yield stiffness ratio

            # Use Steel02 material (Giuffre-Menegotto-Pinto model)
            # Steel02 $matTag $Fy $E $b $R0 $cR1 $cR2 $a1 $a2 $a3 $a4 $sigInit
            R0 = 18.0  # Initial tangent to curved portion
            cR1 = 0.925  # Default calibrated parameters
            cR2 = 0.15

            ops.uniaxialMaterial('Steel02', mat_tag, Fy, E, b, R0, cR1, cR2)

        logger.debug(f"Defined {len(self.model_properties)} Steel02 materials")

    def _create_elements(self):
        """Create elements connecting the nodes (zeroLength + elasticBeamColumn)"""
        self.element_tags = []

        # Geometric transformation for elastic beam elements
        ops.geomTransf('Linear', 1)

        for i, props in enumerate(self.model_properties):
            story_num = props['story']

            # Node tags for this story
            bottom_node = 2 * story_num      # Even numbers: 2, 4, 6, ...
            top_node = 2 * story_num + 1     # Odd numbers: 3, 5, 7, ...

            # Material and element properties
            mat_tag = story_num  # Material tag
            k = props['k']       # Story stiffness (kgf/cm)
            Fy = props['Fy']     # Yield strength (kgf)
            alpha = props['alpha'] # Hardening ratio
            h = props['story_height']  # Story height (cm)
            E = props['E']       # Elastic modulus (kgf/cm²)

            # 1. Create zeroLength element for nonlinear behavior
            # Connects bottom and top nodes at same location (zero length)
            zero_element_tag = 100 + story_num  # Use 100+ series for zeroLength elements
            ops.element('zeroLength', zero_element_tag, bottom_node, top_node, '-mat', mat_tag, '-dir', 1)
            self.element_tags.append(zero_element_tag)

            # 2. Create elastic beam element for connection to next story
            # Only create if this is not the top story
            if story_num < self.num_stories:
                next_bottom_node = 2 * (story_num + 1)  # Bottom node of next story

                # Calculate properties for rigid elastic beam
                # Use very large stiffness to make it essentially rigid
                A = 1.0e8  # Very large area (cm²)
                I = 1.0e8  # Very large moment of inertia (cm⁴)

                beam_element_tag = 200 + story_num  # Use 200+ series for beam elements
                ops.element('elasticBeamColumn', beam_element_tag, top_node, next_bottom_node, A, E, I, 1)
                self.element_tags.append(beam_element_tag)

                logger.debug(f"Story {story_num}: zeroLength {zero_element_tag} ({bottom_node}-{top_node}), beam {beam_element_tag} ({top_node}-{next_bottom_node})")
            else:
                logger.debug(f"Story {story_num}: zeroLength {zero_element_tag} ({bottom_node}-{top_node}), no beam (top story)")

        # Special case: connect ground to first story bottom node
        first_story_bottom = 2  # Bottom node of first story
        ground_beam_tag = 200  # Ground connection beam
        A = 1.0e8  # Very large area
        I = 1.0e8  # Very large moment of inertia
        E = 3.6e5  # Default concrete modulus
        ops.element('elasticBeamColumn', ground_beam_tag, 1, first_story_bottom, A, E, I, 1)
        self.element_tags.append(ground_beam_tag)

        logger.debug(f"Created {len(self.element_tags)} elements: {self.num_stories} zeroLength + {self.num_stories} elastic beams")

    def _apply_masses(self):
        """Apply masses to the top nodes of each story (only to UX DOF for stick model)"""
        for i, props in enumerate(self.model_properties):
            story_num = props['story']
            top_node = 2 * story_num + 1  # Top node of each story (odd numbers: 3, 5, 7, ...)
            mass = props['mass']  # Mass in kgf·s²/cm (already in correct units)

            # Apply mass only to UX (lateral) DOF, zero for UY and RZ
            # Mass is applied to the top node of each story as it represents the floor mass
            ops.mass(top_node, mass, 0.0, 0.0)

            logger.info(f"Mass {mass:.6f} kgf·s²/cm applied to top node {top_node} of story {story_num} (UX only)")

        logger.info(f"Applied masses to {len(self.model_properties)} top story nodes (UX DOF only)")

    def _setup_analysis_parameters(self):
        """Setup basic analysis parameters"""
        # System of equations
        ops.system('BandGeneral')

        # Constraint handler
        ops.constraints('Plain')

        # Numberer
        ops.numberer('RCM')

        # Test for convergence
        ops.test('NormDispIncr', 1.0e-6, 100)

        # Solution algorithm
        ops.algorithm('Newton')

        # Analysis type will be set later for specific analyses
        logger.debug("Basic analysis parameters configured")

    def _validate_system_matrices(self) -> bool:
        """
        Validate mass and stiffness matrices before eigenvalue analysis
        WARNING: Error handling removed for debugging

        Returns:
            bool: True if system is valid for eigenvalue analysis
        """
        # Check if masses are properly applied
        total_mass = 0.0
        zero_mass_nodes = []

        for i, props in enumerate(self.model_properties):
            mass = props['mass']

            # Check for invalid mass values
            if mass <= 0 or np.isnan(mass) or np.isinf(mass):
                logger.error(f"Invalid mass value {mass} for story {props['story']}")
                return False

            # Check for very small masses that might cause numerical issues
            if mass < 1e-6:
                logger.warning(f"Very small mass {mass} for story {props['story']}, may cause numerical issues")

            total_mass += mass

        if total_mass <= 0:
            logger.error(f"Total system mass is {total_mass}, must be positive")
            return False

        logger.debug(f"Mass matrix validation passed: total mass = {total_mass:.2f} kgf·s²/cm")

        # Check stiffness values
        total_stiffness = 0.0
        for props in self.model_properties:
            k = props['k']

            if k <= 0 or np.isnan(k) or np.isinf(k):
                logger.error(f"Invalid stiffness value {k} for story {props['story']}")
                return False

            total_stiffness += k

        if total_stiffness <= 0:
            logger.error(f"Total system stiffness is {total_stiffness}, must be positive")
            return False

        logger.debug(f"Stiffness matrix validation passed: total stiffness = {total_stiffness:.2e} kgf/cm")

        # Check for reasonable mass-to-stiffness ratio
        mass_stiffness_ratio = total_mass / total_stiffness
        expected_period = 2 * np.pi * np.sqrt(mass_stiffness_ratio)

        if expected_period > 10.0:
            logger.warning(f"Expected period {expected_period:.2f}s seems very long, check mass/stiffness values")
        elif expected_period < 0.01:
            logger.warning(f"Expected period {expected_period:.4f}s seems very short, check mass/stiffness values")

        logger.debug(f"Expected fundamental period ≈ {expected_period:.4f}s")

        return True

    def _validate_eigenvalues(self, eigenvalues: List[float]) -> bool:
        """
        Validate eigenvalue results from OpenSees

        Args:
            eigenvalues: List of eigenvalues from ops.eigen()

        Returns:
            bool: True if eigenvalues are valid
        """
        try:
            if not eigenvalues or len(eigenvalues) == 0:
                logger.warning("No eigenvalues returned")
                return False

            # Check for valid numerical values
            for i, eigval in enumerate(eigenvalues):
                if eigval <= 0:
                    logger.warning(f"Non-positive eigenvalue[{i}]: {eigval}")
                    return False

                if np.isnan(eigval) or np.isinf(eigval):
                    logger.warning(f"Invalid eigenvalue[{i}]: {eigval}")
                    return False

                # Check for reasonable magnitude
                if eigval > 1e10 or eigval < 1e-10:
                    logger.warning(f"Eigenvalue[{i}] has unusual magnitude: {eigval}")
                    return False

            logger.debug(f"Eigenvalue validation passed: {len(eigenvalues)} valid eigenvalues")
            return True

        except Exception as e:
            logger.error(f"Eigenvalue validation error: {e}")
            return False

    def perform_eigenvalue_analysis(self) -> Tuple[bool, Optional[float]]:
        """
        Perform eigenvalue analysis to get fundamental period
        WARNING: All error handling removed for debugging - will crash on any OpenSees error

        Returns:
            Tuple[bool, Optional[float]]: (Success flag, Fundamental period)
        """
        # Validate system matrices before eigenvalue analysis
        if not self._validate_system_matrices():
            logger.error("System matrix validation failed, cannot perform eigenvalue analysis")
            return False, None

        # Reset analysis components
        ops.wipeAnalysis()

        # Setup system for analysis
        ops.system('BandGeneral')
        ops.constraints('Plain')
        ops.numberer('RCM')

        # 調試信息：打印模型詳細信息
        logger.info(f"Model details: {self.num_stories} stories")
        for i, props in enumerate(self.model_properties):
            logger.info(f"Story {props['story']}: mass={props['mass']:.6f}, k={props['k']:.1e}, Fy={props['Fy']:.1f}")

        # 檢查節點數量
        try:
            node_count = len(self.node_tags)
            logger.info(f"Total nodes created: {node_count}")
            logger.info(f"Node tags: {self.node_tags}")
        except:
            logger.error("Failed to get node information")

        # 計算合理的模態數量（最多為建築層數，最少為1）
        num_modes = min(max(1, self.num_stories), 3)  # 限制在1-3個模態
        logger.info(f"Requesting {num_modes} eigenvalue modes for {self.num_stories}-story building")

        # Perform eigenvalue analysis - NO ERROR HANDLING
        eigenvalues = ops.eigen('-fullGenLapack', num_modes)

        # Validate eigenvalue results
        if not self._validate_eigenvalues(eigenvalues):
            logger.error(f"Invalid eigenvalues: {eigenvalues}")
            return False, None

        # Calculate fundamental period
        omega1 = np.sqrt(eigenvalues[0])
        T1 = 2.0 * np.pi / omega1

        # Sanity check on period
        if not (0.01 <= T1 <= 10.0):
            logger.error(f"Unrealistic period {T1:.4f}s - check model properties")
            return False, None

        self.fundamental_period = T1
        logger.info(f"Eigenvalue analysis successful: T1 = {T1:.4f} sec")
        return True, T1

    def _estimate_fundamental_period(self) -> Optional[float]:
        """
        Estimate fundamental period using simplified method
        Based on typical building periods and story properties

        Returns:
            Optional[float]: Estimated fundamental period
        """
        try:
            # Simple empirical formula: T1 ≈ 0.1 * N (where N is number of stories)
            T1_empirical = 0.1 * self.num_stories

            # Alternative: Calculate based on stiffness and mass
            # For stick model: T1 ≈ 2π * sqrt(M_total / K_equivalent)
            total_mass = sum(props['mass'] for props in self.model_properties)  # kgf·s²/cm

            # Equivalent stiffness calculation (simplified)
            # For multi-story: 1/K_eq = sum(h_i^3 / (3*E*I)) for cantilever
            story_heights = [300.0] * self.num_stories  # 300cm per story
            k_story = [props['k'] for props in self.model_properties]  # kgf/cm

            # Approximate equivalent stiffness
            k_equivalent = sum(k_story) / self.num_stories  # Simplified average

            T1_calculated = 2 * np.pi * np.sqrt(total_mass / k_equivalent)

            # Use the more reasonable of the two estimates
            T1_estimate = min(T1_empirical, T1_calculated)

            logger.debug(f"Period estimation: empirical={T1_empirical:.4f}s, calculated={T1_calculated:.4f}s")
            return T1_estimate

        except Exception as e:
            logger.error(f"Period estimation failed: {e}")
            return None

    def setup_rayleigh_damping(self, zeta: float = 0.05, mode1: int = 1, mode3: int = 3) -> bool:
        """
        Setup Rayleigh damping based on two target modes

        Args:
            zeta (float): Target damping ratio (default: 0.05 = 5%)
            mode1 (int): First target mode (default: 1)
            mode3 (int): Second target mode (default: 3)

        Returns:
            bool: True if successful
        """
        try:
            # Perform eigenvalue analysis to get frequencies
            num_modes = max(mode1, mode3)
            eigenvalues = ops.eigen(num_modes)

            if len(eigenvalues) < max(mode1, mode3):
                logger.warning(f"Could not extract {max(mode1, mode3)} modes, using available modes")
                if len(eigenvalues) < 2:
                    logger.error("Need at least 2 modes for Rayleigh damping")
                    return False
                mode1, mode3 = 1, min(len(eigenvalues), 3)

            # Calculate natural frequencies
            omega1 = np.sqrt(eigenvalues[mode1-1])
            omega3 = np.sqrt(eigenvalues[mode3-1])

            # Solve for Rayleigh damping coefficients
            # [1/(2*ω1)  ω1/2 ] [α_M]   [ζ]
            # [1/(2*ω3)  ω3/2 ] [β_K] = [ζ]

            A = np.array([[1.0/(2.0*omega1), omega1/2.0],
                         [1.0/(2.0*omega3), omega3/2.0]])
            b = np.array([zeta, zeta])

            coeffs = np.linalg.solve(A, b)
            alpha_M = coeffs[0]  # Mass proportional coefficient
            beta_K = coeffs[1]   # Stiffness proportional coefficient

            # Apply Rayleigh damping: C = α_M*M + β_K*K
            ops.rayleigh(alpha_M, 0.0, 0.0, beta_K)

            logger.debug(f"Rayleigh damping applied: ζ={zeta:.3f}, modes {mode1}&{mode3}")
            logger.debug(f"ω1={omega1:.3f} rad/s, ω3={omega3:.3f} rad/s")
            logger.debug(f"α_M={alpha_M:.6f}, β_K={beta_K:.6f}")

            return True

        except Exception as e:
            logger.error(f"Failed to setup Rayleigh damping: {e}")
            return False

    def get_story_drift_recorders(self) -> List[str]:
        """
        Setup recorders for story drift monitoring

        Returns:
            List[str]: List of recorder file names
        """
        recorder_files = []

        for i in range(self.num_stories):
            node_i = i + 1  # Bottom node
            node_j = i + 2  # Top node

            # Record relative displacement between stories
            recorder_file = f"story_{i+1}_drift.out"
            recorder_files.append(recorder_file)

            # Record displacement for drift calculation
            ops.recorder('Node', '-file', recorder_file, '-node', node_j, '-dof', 1, 'disp')

        return recorder_files

    def calculate_interstory_drift_ratio(self, displacements: np.ndarray, story_heights: Optional[List[float]] = None) -> np.ndarray:
        """
        Calculate interstory drift ratios from displacement time history

        Args:
            displacements (np.ndarray): Displacement time history [n_stories x n_time]
            story_heights (List[float], optional): Story heights in meters

        Returns:
            np.ndarray: Interstory drift ratios [n_stories x n_time]
        """
        if story_heights is None:
            story_heights = [300.0] * self.num_stories  # Default 300cm per story

        if len(story_heights) != self.num_stories:
            raise ValueError("Number of story heights must match number of stories")

        # Calculate relative displacements between stories
        n_time = displacements.shape[1] if displacements.ndim > 1 else len(displacements)
        drift_ratios = np.zeros((self.num_stories, n_time))

        for i in range(self.num_stories):
            if i == 0:
                # First story: displacement relative to ground
                relative_disp = displacements[i, :] if displacements.ndim > 1 else displacements[0]
            else:
                # Other stories: displacement relative to story below
                relative_disp = displacements[i, :] - displacements[i-1, :] if displacements.ndim > 1 else displacements[i] - displacements[i-1]

            # Calculate drift ratio
            drift_ratios[i, :] = relative_disp / story_heights[i]

        return drift_ratios

    def get_model_summary(self) -> str:
        """
        Get a summary of the model properties

        Returns:
            str: Model summary
        """
        period_str = f"{self.fundamental_period:.4f}" if self.fundamental_period else "Not computed"
        summary = f"""
Stick Model Summary
===================
Number of Stories: {self.num_stories}
Damping Ratio: {self.damping_ratio:.3f}
Fundamental Period: {period_str} sec

Story Properties:
"""
        for props in self.model_properties:
            summary += f"  Story {props['story']}: Mass={props['mass']:.1f} kgf·s²/cm, "
            summary += f"K={props['k']:.0f} kgf/cm, Fy={props['Fy']:.0f} kgf, α={props['alpha']:.3f}\n"

        return summary


def main():
    """Test the structural model"""
    # Define 5-story building with enhanced parameters
    # Example 1: Steel structure
    steel_model = [
        {'story': 1, 'mass': 120.0, 'k': 6.5e4, 'Fy': 4800.0, 'alpha': 0.025,
         'material_type': 'steel', 'story_height': 400.0},
        {'story': 2, 'mass': 120.0, 'k': 6.5e4, 'Fy': 4800.0, 'alpha': 0.025,
         'material_type': 'steel', 'story_height': 350.0},
        {'story': 3, 'mass': 120.0, 'k': 6.2e4, 'Fy': 4600.0, 'alpha': 0.025,
         'material_type': 'steel', 'story_height': 350.0},
        {'story': 4, 'mass': 120.0, 'k': 6.2e4, 'Fy': 4600.0, 'alpha': 0.025,
         'material_type': 'steel', 'story_height': 350.0},
        {'story': 5, 'mass': 130.0, 'k': 6.0e4, 'Fy': 4500.0, 'alpha': 0.025,
         'material_type': 'steel', 'story_height': 350.0},
    ]

    # Example 2: Concrete structure (minimal parameters - will use defaults)
    concrete_model = [
        {'story': 1, 'mass': 120.0, 'k': 6.5e4, 'Fy': 4800.0, 'alpha': 0.025},
        {'story': 2, 'mass': 120.0, 'k': 6.5e4, 'Fy': 4800.0, 'alpha': 0.025},
        {'story': 3, 'mass': 120.0, 'k': 6.2e4, 'Fy': 4600.0, 'alpha': 0.025},
    ]

    # Test steel structure
    print("=== Testing Steel Structure ===")
    stick_model = StickModel(steel_model, damping_ratio=0.05)

    success = stick_model.build_model()
    if success:
        print("✓ Model built successfully")

        # Perform eigenvalue analysis
        eigenvalue_success, T1 = stick_model.perform_eigenvalue_analysis()
        if eigenvalue_success:
            print(f"✓ Fundamental period: T1 = {T1:.4f} sec")

            # Setup Rayleigh damping
            damping_success = stick_model.setup_rayleigh_damping(zeta=0.05, mode1=1, mode3=3)
            if damping_success:
                print("✓ Rayleigh damping configured")
        else:
            print("✗ Eigenvalue analysis failed")

        # Print model summary
        print(stick_model.get_model_summary())

    else:
        print("✗ Model building failed")

    print("\n=== Testing Concrete Structure (defaults) ===")
    concrete_stick = StickModel(concrete_model, damping_ratio=0.05)
    success = concrete_stick.build_model()
    if success:
        print("✓ Concrete model built successfully")
        print(concrete_stick.get_model_summary())
    else:
        print("✗ Concrete model building failed")


if __name__ == "__main__":
    main()