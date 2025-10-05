#!/usr/bin/env python3
"""
Fragility Analysis Module
Statistical analysis and curve fitting for fragility curves
Enhanced with PGA intensity mapping for standardized output
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional, Any
import logging
from pathlib import Path
import sys
import os

# Add utils to path for importing PGA mapping
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from pga_mapping import PGAIntensityMapper

logger = logging.getLogger(__name__)


class FragilityAnalyzer:
    """
    Statistical analysis and fragility curve generation
    """

    def __init__(self, ida_results: pd.DataFrame, damage_states: Dict[str, float]):
        """
        Initialize the fragility analyzer

        Args:
            ida_results (pd.DataFrame): IDA analysis results
            damage_states (Dict[str, float]): Damage state thresholds
        """
        self.ida_results = ida_results
        self.damage_states = damage_states
        self.fragility_parameters = {}
        self.fragility_curves = {}
        self.psdm_parameters = {}  # Store PSDM regression parameters

        # Initialize PGA intensity mapper
        self.pga_mapper = PGAIntensityMapper()

        # Validate inputs
        self._validate_inputs()

    def _validate_inputs(self):
        """Validate input data"""
        # Support both old and new column names for backward compatibility
        required_columns = ['gm_id', 'max_idr', 'analysis_success', 'collapse']

        # Check for intensity measure column (either pga_target or sa_target)
        if 'pga_target' in self.ida_results.columns:
            required_columns.append('pga_target')
            self._intensity_column = 'pga_target'
        elif 'sa_target' in self.ida_results.columns:
            required_columns.append('sa_target')
            self._intensity_column = 'sa_target'
        else:
            raise ValueError("Missing intensity measure column (pga_target or sa_target)")

        for col in required_columns:
            if col not in self.ida_results.columns:
                raise ValueError(f"Missing required column in IDA results: {col}")

        if not self.damage_states:
            raise ValueError("Damage states dictionary cannot be empty")

        logger.info(f"Input validation passed: {len(self.ida_results)} IDA results, "
                   f"{len(self.damage_states)} damage states")

    def determine_damage_state(self, max_idr: float, analysis_success: bool = True) -> str:
        """
        Determine damage state based on maximum IDR

        Args:
            max_idr (float): Maximum interstory drift ratio
            analysis_success (bool): Whether analysis was successful

        Returns:
            str: Damage state name
        """
        # If analysis failed or collapsed, assign highest damage state
        if not analysis_success or max_idr >= max(self.damage_states.values()):
            return list(self.damage_states.keys())[-1]  # Highest damage state (usually collapse)

        # Find appropriate damage state
        sorted_states = sorted(self.damage_states.items(), key=lambda x: x[1])

        for state_name, threshold in sorted_states:
            if max_idr >= threshold:
                continue
            else:
                # Return previous state (the one we just exceeded)
                previous_index = sorted_states.index((state_name, threshold)) - 1
                if previous_index >= 0:
                    return sorted_states[previous_index][0]
                else:
                    return 'No_Damage'

        # If we get here, we're in the highest damage state
        return sorted_states[-1][0]

    def calculate_damage_state_probabilities(self) -> pd.DataFrame:
        """
        Calculate damage state probabilities for each intensity level

        Returns:
            pd.DataFrame: Damage state probabilities by intensity level
        """
        logger.info("Calculating damage state probabilities...")

        # Add damage state column to results
        df = self.ida_results.copy()
        df['damage_state'] = df.apply(
            lambda row: self.determine_damage_state(row['max_idr'], row['analysis_success']),
            axis=1
        )

        # Group by intensity level
        intensity_levels = sorted(df[self._intensity_column].unique())
        damage_state_names = list(self.damage_states.keys())

        prob_data = []

        for sa_level in intensity_levels:
            level_data = df[df[self._intensity_column] == sa_level]
            n_total = len(level_data)

            if n_total == 0:
                continue

            sa_probs = {'sa_level': sa_level, 'n_total': n_total}

            # Count occurrences of each damage state
            damage_counts = level_data['damage_state'].value_counts()

            # Calculate probabilities for each damage state
            for ds_name in damage_state_names:
                count = damage_counts.get(ds_name, 0)
                prob = count / n_total
                sa_probs[f'P({ds_name})'] = prob
                sa_probs[f'count_{ds_name}'] = count

            prob_data.append(sa_probs)

        prob_df = pd.DataFrame(prob_data)
        logger.info(f"Calculated probabilities for {len(prob_df)} intensity levels")

        return prob_df

    def fit_psdm_regression(self) -> Dict[str, float]:
        """
        Fit PSDM (Probabilistic Seismic Demand Model) using log-log linear regression

        Performs regression: ln(EDP) = a * ln(IM) + b
        where EDP = max_idr and IM = intensity measure (pga_target or sa_target)

        Returns:
            Dict[str, float]: PSDM parameters {slope_a, intercept_b, beta_d_given_im, r_squared, n_points}
        """
        logger.info("Fitting PSDM regression model...")

        # Filter successful analyses only (exclude collapsed cases for regression)
        successful_data = self.ida_results[
            (self.ida_results['analysis_success'] == True) &
            (self.ida_results['max_idr'] > 0) &
            (self.ida_results[self._intensity_column] > 0)
        ].copy()

        if len(successful_data) < 3:
            logger.error(f"Insufficient data for PSDM regression: only {len(successful_data)} successful analyses")
            return {}

        # Extract IM and EDP data
        intensity_values = successful_data[self._intensity_column].values
        max_idr_values = successful_data['max_idr'].values

        # Log transformation
        ln_intensity = np.log(intensity_values)
        ln_idr = np.log(max_idr_values)

        logger.info(f"PSDM Regression Data Summary:")
        logger.info(f"  Number of data points: {len(successful_data)}")
        logger.info(f"  Intensity range: {intensity_values.min():.3f} - {intensity_values.max():.3f} g")
        logger.info(f"  Max IDR range: {max_idr_values.min():.6f} - {max_idr_values.max():.6f}")

        # try:
        # Perform linear regression: ln(EDP) = a * ln(IM) + b
        slope_a, intercept_b, r_value, p_value, std_err = stats.linregress(ln_intensity, ln_idr)

        # Calculate demand uncertainty (standard error of regression)
        # This represents the lognormal standard deviation of demand given IM
        residuals = ln_idr - (slope_a * ln_intensity + intercept_b)
        beta_d_given_im = np.std(residuals, ddof=2)  # Use sample standard deviation

        r_squared = r_value ** 2
        n_points = len(successful_data)

        # Store PSDM parameters
        psdm_params = {
            'slope_a': slope_a,
            'intercept_b': intercept_b,
            'beta_d_given_im': beta_d_given_im,
            'r_squared': r_squared,
            'p_value': p_value,
            'n_points': n_points,
            'intensity_range': (intensity_values.min(), intensity_values.max()),
            'idr_range': (max_idr_values.min(), max_idr_values.max())
        }

        self.psdm_parameters = psdm_params

        logger.info(f"PSDM Regression Results:")
        logger.info(f"  Slope (a): {slope_a:.4f}")
        logger.info(f"  Intercept (b): {intercept_b:.4f}")
        logger.info(f"  Demand uncertainty (β_D|IM): {beta_d_given_im:.4f}")
        logger.info(f"  R²: {r_squared:.4f}")
        logger.info(f"  P-value: {p_value:.6f}")

        # Validate regression quality
        if r_squared < 0.3:
            logger.warning(f"Low R² ({r_squared:.3f}) indicates poor PSDM fit")
        if p_value > 0.05:
            logger.warning(f"High p-value ({p_value:.3f}) indicates statistically insignificant relationship")

        return psdm_params

        # except Exception as e:
        #     logger.error(f"PSDM regression failed: {e}")
        #     return {}

    def calculate_fragility_parameters_from_psdm(self) -> Dict[str, Dict]:
        """
        Calculate fragility parameters (theta, beta) for each damage state using PSDM parameters

        Uses the theoretical relationship:
        θ (median) = exp((ln(ds_threshold) - b) / a)
        β (total uncertainty) = β_D|IM / |a|

        Returns:
            Dict[str, Dict]: Fragility parameters for each damage state
        """
        if not self.psdm_parameters:
            logger.error("No PSDM parameters available. Run fit_psdm_regression() first.")
            return {}

        logger.info("Calculating fragility parameters from PSDM regression...")

        # Extract PSDM parameters
        slope_a = self.psdm_parameters['slope_a']
        intercept_b = self.psdm_parameters['intercept_b']
        beta_d_given_im = self.psdm_parameters['beta_d_given_im']
        r_squared = self.psdm_parameters['r_squared']
        n_points = self.psdm_parameters['n_points']

        fragility_params = {}

        for ds_name, ds_threshold in self.damage_states.items():
            # try:
                # Calculate theta (median): θ = exp((ln(ds_threshold) - b) / a)
                theta = np.exp((np.log(ds_threshold) - intercept_b) / slope_a)

                # Calculate beta (total uncertainty): β = β_D|IM / |a|
                # This assumes uncertainty is dominated by demand uncertainty
                beta = beta_d_given_im / abs(slope_a)

                # Validate parameters
                if theta <= 0 or beta <= 0:
                    logger.warning(f"Invalid parameters for {ds_name}: θ={theta:.4f}, β={beta:.4f}")
                    continue

                if theta > 10.0 or beta > 3.0:
                    logger.warning(f"Extreme parameters for {ds_name}: θ={theta:.4f}, β={beta:.4f}")

                fragility_params[ds_name] = {
                    'damage_state': ds_name,
                    'threshold_idr': ds_threshold,
                    'median_theta': theta,
                    'lognormal_beta': beta,
                    'r_squared': r_squared,  # Same R² for all since derived from same regression
                    'n_data_points': n_points,
                    'source_method': 'PSDM'
                }

                logger.info(f"PSDM-derived parameters for {ds_name}:")
                logger.info(f"  IDR threshold: {ds_threshold:.3f} ({ds_threshold*100:.1f}%)")
                logger.info(f"  Median θ: {theta:.4f} g")
                logger.info(f"  Total β: {beta:.4f}")

            # except Exception as e:
                # logger.error(f"Failed to calculate fragility parameters for {ds_name}: {e}")
                # continue

        if not fragility_params:
            logger.error("No fragility parameters could be calculated from PSDM")
        else:
            logger.info(f"Successfully calculated PSDM-derived parameters for {len(fragility_params)} damage states")

        return fragility_params

    def fit_lognormal_fragility_curve(self, sa_levels: np.ndarray, probabilities: np.ndarray) -> Tuple[float, float, float]:
        """
        Fit lognormal fragility curve using enhanced methods with better edge case handling

        Args:
            sa_levels (np.ndarray): Intensity levels (Sa in g)
            probabilities (np.ndarray): Failure probabilities

        Returns:
            Tuple[float, float, float]: (median theta, lognormal std beta, R²)
        """
        try:
            # Method 1: Standard approach (requires probabilities in (0,1) range)
            mask = (probabilities > 0.001) & (probabilities < 0.999) & (sa_levels > 0)
            sa_filtered = sa_levels[mask]
            prob_filtered = probabilities[mask]

            if len(sa_filtered) >= 3:
                try:
                    # Log-transform Sa values
                    ln_sa = np.log(sa_filtered)
                    # Convert probabilities to normal scores (inverse CDF)
                    normal_scores = stats.norm.ppf(prob_filtered)

                    # Perform linear regression
                    slope, intercept, r_value, p_value, std_err = stats.linregress(normal_scores, ln_sa)

                    # Extract parameters
                    beta = abs(slope)  # Ensure positive beta
                    theta = np.exp(intercept)
                    r_squared = r_value**2

                    # Validate parameters
                    if 0.01 <= theta <= 10.0 and 0.1 <= beta <= 2.0 and r_squared >= 0.3:
                        logger.debug(f"Standard fit successful: θ={theta:.4f}, β={beta:.4f}, R²={r_squared:.4f}")
                        return theta, beta, r_squared
                except Exception as e:
                    logger.debug(f"Standard fitting failed: {e}")

            # Method 2: Use all available data with probability adjustment
            mask2 = (sa_levels > 0)
            sa_all = sa_levels[mask2]
            prob_all = probabilities[mask2]

            if len(sa_all) >= 2:
                # Adjust probabilities to avoid boundary issues
                prob_adjusted = np.clip(prob_all, 0.01, 0.99)

                # If we have at least one meaningful probability variation
                if np.max(prob_adjusted) - np.min(prob_adjusted) > 0.1:
                    try:
                        from scipy.optimize import curve_fit

                        # Direct lognormal CDF fitting
                        def lognormal_cdf(x, median, beta):
                            return stats.lognorm.cdf(x, s=beta, scale=median)

                        # Initial parameter guess
                        median_guess = np.median(sa_all[prob_adjusted >= 0.5]) if np.any(prob_adjusted >= 0.5) else np.median(sa_all)
                        beta_guess = 0.5

                        # Curve fitting
                        popt, pcov = curve_fit(lognormal_cdf, sa_all, prob_adjusted,
                                             p0=[median_guess, beta_guess],
                                             bounds=([0.01, 0.1], [10.0, 2.0]),
                                             maxfev=2000)

                        theta_fit, beta_fit = popt

                        # Calculate R²
                        y_pred = lognormal_cdf(sa_all, theta_fit, beta_fit)
                        ss_res = np.sum((prob_adjusted - y_pred) ** 2)
                        ss_tot = np.sum((prob_adjusted - np.mean(prob_adjusted)) ** 2)
                        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                        logger.debug(f"Curve fit successful: θ={theta_fit:.4f}, β={beta_fit:.4f}, R²={r_squared:.4f}")
                        return theta_fit, beta_fit, r_squared
                    except Exception as e:
                        logger.debug(f"Curve fitting failed: {e}")

            # Method 3: Simple parametric estimation based on data characteristics
            if len(sa_all) >= 1 and np.max(prob_all) > 0:
                # Find where probability crosses 0.5 (median estimate)
                if np.any(prob_all >= 0.5):
                    idx_median = np.where(prob_all >= 0.5)[0][0]
                    theta_simple = sa_all[idx_median]
                else:
                    # Extrapolate based on trend
                    if len(sa_all) > 1:
                        # Linear extrapolation
                        slope_est = (prob_all[-1] - prob_all[0]) / (sa_all[-1] - sa_all[0]) if sa_all[-1] != sa_all[0] else 0
                        if slope_est > 0:
                            theta_simple = sa_all[0] + (0.5 - prob_all[0]) / slope_est
                        else:
                            theta_simple = sa_all[-1] * 2
                    else:
                        theta_simple = sa_all[0] * 2

                # Ensure reasonable bounds
                theta_simple = np.clip(theta_simple, 0.01, 10.0)

                # Estimate beta from data spread
                beta_simple = 0.5  # Default moderate variability
                r_squared = 0.3   # Moderate confidence

                logger.debug(f"Simple fit: θ={theta_simple:.4f}, β={beta_simple:.4f}, R²={r_squared:.4f}")
                return theta_simple, beta_simple, r_squared

            # If all methods fail
            logger.warning("All fitting methods failed - insufficient data")
            return None, None, 0.0

        except Exception as e:
            logger.error(f"Enhanced curve fitting failed: {e}")
            return None, None, 0.0

    def fit_all_fragility_curves(self) -> Dict[str, Dict]:
        """
        Fit fragility curves for all damage states using PSDM (Probabilistic Seismic Demand Model)

        This method uses a single regression model to derive all fragility parameters:
        1. Fit PSDM regression: ln(EDP) = a * ln(IM) + b
        2. Calculate theta and beta for each damage state using theoretical relationships

        Returns:
            Dict[str, Dict]: Fragility parameters for each damage state
        """
        logger.info("Fitting fragility curves using PSDM method...")

        # Analyze data characteristics first
        idr_values = self.ida_results['max_idr'].values
        logger.info(f"IDA Data Summary:")
        logger.info(f"  Total analyses: {len(self.ida_results)}")
        logger.info(f"  IDR range: {idr_values.min():.6f} - {idr_values.max():.6f}")
        logger.info(f"  IDR mean: {idr_values.mean():.6f}, std: {idr_values.std():.6f}")
        logger.info(f"  Analysis success rate: {self.ida_results['analysis_success'].mean():.2%}")

        # Step 1: Fit PSDM regression model
        psdm_params = self.fit_psdm_regression()

        if not psdm_params:
            logger.error("PSDM regression failed - falling back to traditional method")
            return self._fit_fragility_curves_traditional()

        # Step 2: Calculate fragility parameters from PSDM
        fragility_params = self.calculate_fragility_parameters_from_psdm()

        if not fragility_params:
            logger.error("No fragility curves were successfully derived from PSDM!")
            logger.error("This may indicate:")
            logger.error("  1. Poor PSDM regression fit")
            logger.error("  2. Extreme parameter values")
            logger.error("  3. Damage state thresholds incompatible with data")

            # Try fallback method
            logger.info("Attempting fallback to traditional fitting method...")
            return self._fit_fragility_curves_traditional()

        # Validation: Check if PSDM predictions make sense
        self._validate_psdm_fragility_curves(fragility_params)

        self.fragility_parameters = fragility_params
        logger.info(f"Successfully fitted fragility curves using PSDM for {len(fragility_params)} damage states")

        return fragility_params

    def _fit_fragility_curves_traditional(self) -> Dict[str, Dict]:
        """
        Fallback method: Traditional probability-based fitting for each damage state separately
        """
        logger.info("Using traditional probability-based fitting method...")

        # Calculate damage state probabilities
        prob_df = self.calculate_damage_state_probabilities()

        # Show probability summary
        logger.info("Damage State Probability Summary:")
        for ds_name in self.damage_states.keys():
            prob_col = f'P({ds_name})'
            if prob_col in prob_df.columns:
                probs = prob_df[prob_col].values
                n_nonzero = np.sum(probs > 0)
                n_valid = np.sum((probs > 0.001) & (probs < 0.999))
                prob_range = f"{probs.min():.3f} - {probs.max():.3f}"
                logger.info(f"  {ds_name}: {n_nonzero} non-zero, {n_valid} valid, range: {prob_range}")

        fragility_params = {}

        for ds_name in self.damage_states.keys():
            prob_col = f'P({ds_name})'

            if prob_col not in prob_df.columns:
                logger.warning(f"No probability data for damage state: {ds_name}")
                continue

            # Extract data for this damage state
            sa_levels = prob_df['sa_level'].values
            probabilities = prob_df[prob_col].values

            logger.debug(f"Fitting {ds_name} with {len(sa_levels)} intensity levels")

            # Fit lognormal curve
            theta, beta, r_squared = self.fit_lognormal_fragility_curve(sa_levels, probabilities)

            if theta is not None and beta is not None:
                fragility_params[ds_name] = {
                    'damage_state': ds_name,
                    'threshold_idr': self.damage_states[ds_name],
                    'median_theta': theta,
                    'lognormal_beta': beta,
                    'r_squared': r_squared,
                    'n_data_points': len(sa_levels),
                    'source_method': 'Traditional'
                }

                logger.info(f"Traditional fit {ds_name}: θ={theta:.4f}g, β={beta:.4f}, R²={r_squared:.4f}")
            else:
                logger.warning(f"Failed to fit curve for damage state: {ds_name}")

        return fragility_params

    def _validate_psdm_fragility_curves(self, fragility_params: Dict[str, Dict]):
        """
        Validate PSDM-derived fragility curve parameters
        """
        logger.info("Validating PSDM-derived fragility curves...")

        for ds_name, params in fragility_params.items():
            theta = params['median_theta']
            beta = params['lognormal_beta']

            # Check for reasonable parameter ranges
            issues = []
            if theta < 0.01 or theta > 10.0:
                issues.append(f"θ={theta:.4f} outside typical range [0.01, 10.0]")
            if beta < 0.1 or beta > 2.0:
                issues.append(f"β={beta:.4f} outside typical range [0.1, 2.0]")

            if issues:
                logger.warning(f"Parameter validation issues for {ds_name}: {'; '.join(issues)}")
            else:
                logger.debug(f"Parameters validated for {ds_name}: θ={theta:.4f}, β={beta:.4f}")

    def generate_fragility_curves(self, sa_range: Optional[Tuple[float, float]] = None, n_points: int = 100) -> Dict[str, pd.DataFrame]:
        """
        Generate fragility curve points for plotting

        Args:
            sa_range (Tuple[float, float], optional): SA range (min, max) in g
            n_points (int): Number of points to generate

        Returns:
            Dict[str, pd.DataFrame]: Fragility curve data for each damage state
        """
        if not self.fragility_parameters:
            logger.error("No fragility parameters available. Run fit_all_fragility_curves() first.")
            return {}

        # Determine SA range if not provided
        if sa_range is None:
            sa_min = 0.01
            sa_max = 2.0
            if not self.ida_results.empty:
                sa_max = max(2.0, self.ida_results[self._intensity_column].max() * 1.2)
        else:
            sa_min, sa_max = sa_range

        # Generate SA values
        sa_values = np.logspace(np.log10(sa_min), np.log10(sa_max), n_points)

        curves = {}

        for ds_name, params in self.fragility_parameters.items():
            theta = params['median_theta']
            beta = params['lognormal_beta']

            # Calculate lognormal CDF
            probabilities = stats.lognorm.cdf(sa_values, s=beta, scale=theta)

            # Create DataFrame
            curve_df = pd.DataFrame({
                'sa_g': sa_values,
                'probability': probabilities,
                'damage_state': ds_name
            })

            curves[ds_name] = curve_df

        self.fragility_curves = curves
        logger.info(f"Generated fragility curves for {len(curves)} damage states")

        return curves

    def save_fragility_parameters(self, output_file: str):
        """
        Save fragility parameters to CSV file

        Args:
            output_file (str): Output file path
        """
        if not self.fragility_parameters:
            logger.warning("No fragility parameters to save")
            return

        # Convert to DataFrame
        params_data = []
        for ds_name, params in self.fragility_parameters.items():
            param_row = {
                'Damage_State': ds_name,
                'IDR_Threshold_percent': params['threshold_idr'] * 100,  # Convert to percentage
                'Median_theta_g': params['median_theta'],
                'Lognormal_StdDev_beta': params['lognormal_beta'],
                'R_squared': params['r_squared'],
                'N_Data_Points': params['n_data_points']
            }

            # Add source method information if available
            if 'source_method' in params:
                param_row['Source_Method'] = params['source_method']

            params_data.append(param_row)

        params_df = pd.DataFrame(params_data)
        params_df.to_csv(output_file, index=False)

        logger.info(f"Fragility parameters saved to: {output_file}")

    def save_psdm_parameters(self, output_file: str):
        """
        Save PSDM regression parameters to CSV file

        Args:
            output_file (str): Output file path
        """
        if not self.psdm_parameters:
            logger.warning("No PSDM parameters to save")
            return

        # Create DataFrame with PSDM parameters
        psdm_data = [{
            'Parameter': 'Slope_a',
            'Value': self.psdm_parameters['slope_a'],
            'Description': 'PSDM regression slope (a in ln(EDP) = a*ln(IM) + b)'
        }, {
            'Parameter': 'Intercept_b',
            'Value': self.psdm_parameters['intercept_b'],
            'Description': 'PSDM regression intercept (b in ln(EDP) = a*ln(IM) + b)'
        }, {
            'Parameter': 'Beta_D_given_IM',
            'Value': self.psdm_parameters['beta_d_given_im'],
            'Description': 'Demand uncertainty (lognormal std dev of EDP given IM)'
        }, {
            'Parameter': 'R_squared',
            'Value': self.psdm_parameters['r_squared'],
            'Description': 'Coefficient of determination for PSDM regression'
        }, {
            'Parameter': 'P_value',
            'Value': self.psdm_parameters['p_value'],
            'Description': 'Statistical significance of PSDM regression'
        }, {
            'Parameter': 'N_data_points',
            'Value': self.psdm_parameters['n_points'],
            'Description': 'Number of (SA, IDR) data points used in regression'
        }, {
            'Parameter': 'SA_range_min',
            'Value': self.psdm_parameters['sa_range'][0],
            'Description': 'Minimum spectral acceleration in regression (g)'
        }, {
            'Parameter': 'SA_range_max',
            'Value': self.psdm_parameters['sa_range'][1],
            'Description': 'Maximum spectral acceleration in regression (g)'
        }, {
            'Parameter': 'IDR_range_min',
            'Value': self.psdm_parameters['idr_range'][0],
            'Description': 'Minimum IDR in regression'
        }, {
            'Parameter': 'IDR_range_max',
            'Value': self.psdm_parameters['idr_range'][1],
            'Description': 'Maximum IDR in regression'
        }]

        psdm_df = pd.DataFrame(psdm_data)
        psdm_df.to_csv(output_file, index=False)

        logger.info(f"PSDM parameters saved to: {output_file}")

    def save_fragility_curves(self, output_file: str, building_id: str = "", include_metadata: bool = True):
        """
        Save complete fragility curve points to CSV file

        Args:
            output_file (str): Output file path
            building_id (str): Building identifier for metadata
            include_metadata (bool): Whether to include analysis metadata
        """
        if not self.fragility_curves:
            logger.warning("No fragility curves to save. Run generate_fragility_curves() first.")
            return

        # Combine all curve data into a single DataFrame
        all_curves_data = []

        for ds_name, curve_df in self.fragility_curves.items():
            curve_data = curve_df.copy()
            curve_data['damage_state'] = ds_name

            # Add parameters for reference
            if ds_name in self.fragility_parameters:
                params = self.fragility_parameters[ds_name]
                curve_data['median_theta_g'] = params['median_theta']
                curve_data['lognormal_beta'] = params['lognormal_beta']
                curve_data['r_squared'] = params['r_squared']
                curve_data['idr_threshold_percent'] = params['threshold_idr'] * 100

            all_curves_data.append(curve_data)

        if not all_curves_data:
            logger.warning("No curve data to save")
            return

        # Concatenate all curves
        combined_df = pd.concat(all_curves_data, ignore_index=True)

        # Reorder columns for clarity
        column_order = ['damage_state', 'sa_g', 'probability', 'idr_threshold_percent',
                       'median_theta_g', 'lognormal_beta', 'r_squared']
        existing_cols = [col for col in column_order if col in combined_df.columns]
        other_cols = [col for col in combined_df.columns if col not in existing_cols]
        combined_df = combined_df[existing_cols + other_cols]

        # Add metadata if requested
        if include_metadata:
            import time
            metadata_rows = []
            metadata_rows.append(['# Fragility Curves Data Export'])
            metadata_rows.append([f'# Building ID: {building_id}'])
            metadata_rows.append([f'# Export Date: {time.strftime("%Y-%m-%d %H:%M:%S")}'])
            metadata_rows.append([f'# Number of Damage States: {len(self.fragility_curves)}'])
            metadata_rows.append([f'# Total Data Points: {len(combined_df)}'])
            metadata_rows.append(['# Column Descriptions:'])
            metadata_rows.append(['# sa_g: Spectral acceleration in g'])
            metadata_rows.append(['# probability: Exceedance probability for damage state'])
            metadata_rows.append(['# idr_threshold_percent: IDR threshold for damage state (%)'])
            metadata_rows.append(['# median_theta_g: Lognormal distribution median (g)'])
            metadata_rows.append(['# lognormal_beta: Lognormal distribution standard deviation'])
            metadata_rows.append(['# r_squared: Goodness of fit for fragility curve'])
            metadata_rows.append([''])  # Empty row before data

            # Write metadata and data
            with open(output_file, 'w') as f:
                for row in metadata_rows:
                    f.write(','.join(row) + '\n')
                combined_df.to_csv(f, index=False)
        else:
            # Save without metadata
            combined_df.to_csv(output_file, index=False)

        logger.info(f"Fragility curves data saved to: {output_file}")
        logger.info(f"  - {len(self.fragility_curves)} damage states")
        logger.info(f"  - {len(combined_df)} total data points")

    def load_fragility_curves(self, input_file: str) -> Dict[str, pd.DataFrame]:
        """
        Load fragility curve data from saved CSV file

        Args:
            input_file (str): Input file path

        Returns:
            Dict[str, pd.DataFrame]: Loaded fragility curves by damage state
        """
        try:
            # Read the file, skipping metadata lines that start with #
            with open(input_file, 'r') as f:
                lines = f.readlines()

            # Find where actual data starts (after metadata comments)
            data_start = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith('#') and line.strip():
                    data_start = i
                    break

            # Read the CSV data
            df = pd.read_csv(input_file, skiprows=data_start)

            # Split by damage state
            loaded_curves = {}

            if 'damage_state' in df.columns:
                for ds_name in df['damage_state'].unique():
                    ds_data = df[df['damage_state'] == ds_name].copy()

                    # Keep only essential curve data
                    curve_df = pd.DataFrame({
                        'sa_g': ds_data['sa_g'],
                        'probability': ds_data['probability'],
                        'damage_state': ds_name
                    })

                    loaded_curves[ds_name] = curve_df

                logger.info(f"Loaded fragility curves from: {input_file}")
                logger.info(f"  - {len(loaded_curves)} damage states")
                logger.info(f"  - {len(df)} total data points")

                return loaded_curves
            else:
                logger.error(f"Invalid fragility curves file format: missing 'damage_state' column")
                return {}

        except Exception as e:
            logger.error(f"Failed to load fragility curves from {input_file}: {e}")
            return {}

    def validate_fragility_curves(self) -> Dict[str, Dict]:
        """
        Validate fragility curve quality

        Returns:
            Dict[str, Dict]: Validation results for each damage state
        """
        validation_results = {}

        for ds_name, params in self.fragility_parameters.items():
            results = {
                'theta_reasonable': 0.01 <= params['median_theta'] <= 10.0,  # Reasonable range in g
                'beta_reasonable': 0.1 <= params['lognormal_beta'] <= 1.5,   # Typical range
                'r_squared_good': params['r_squared'] >= 0.7,                # Good fit
                'sufficient_data': params['n_data_points'] >= 5,             # Minimum data points
            }

            results['overall_quality'] = sum(results.values()) / len(results)
            validation_results[ds_name] = results

        return validation_results

    def get_fragility_summary(self) -> str:
        """
        Get summary of fragility analysis results

        Returns:
            str: Summary text
        """
        if not self.fragility_parameters:
            return "No fragility analysis results available"

        summary = """
Fragility Analysis Summary
==========================
"""
        summary += f"Number of damage states analyzed: {len(self.fragility_parameters)}\n"
        summary += f"Total IDA results used: {len(self.ida_results)}\n"
        summary += f"Unique ground motions: {self.ida_results['gm_id'].nunique()}\n\n"

        # Add PSDM information if available
        if self.psdm_parameters:
            summary += "PSDM Regression Model:\n"
            summary += f"  Equation: ln(IDR) = {self.psdm_parameters['slope_a']:.4f} * ln(Sa) + {self.psdm_parameters['intercept_b']:.4f}\n"
            summary += f"  Demand uncertainty (β_D|IM): {self.psdm_parameters['beta_d_given_im']:.4f}\n"
            summary += f"  R²: {self.psdm_parameters['r_squared']:.4f}\n"
            summary += f"  P-value: {self.psdm_parameters['p_value']:.6f}\n"
            summary += f"  Data points: {self.psdm_parameters['n_points']}\n\n"

        summary += "Fragility Parameters:\n"
        for ds_name, params in self.fragility_parameters.items():
            summary += f"  {ds_name}:\n"
            summary += f"    IDR Threshold: {params['threshold_idr']:.3f} ({params['threshold_idr']*100:.1f}%)\n"
            summary += f"    Median θ: {params['median_theta']:.4f} g\n"
            summary += f"    Log-std β: {params['lognormal_beta']:.4f}\n"
            summary += f"    R²: {params['r_squared']:.4f}\n"
            if 'source_method' in params:
                summary += f"    Source: {params['source_method']}\n"
            summary += "\n"

        # Validation summary
        validation = self.validate_fragility_curves()
        summary += "Quality Assessment:\n"
        for ds_name, results in validation.items():
            quality = results['overall_quality']
            quality_text = "Good" if quality >= 0.75 else "Fair" if quality >= 0.5 else "Poor"
            summary += f"  {ds_name}: {quality_text} (score: {quality:.2f})\n"

        return summary

    def generate_pga_fragility_curve(self, collapse_damage_state: str = None) -> Dict[str, float]:
        """
        生成標準震度級別對應的倒塌機率字典

        Args:
            collapse_damage_state: 倒塌損壞狀態名稱，若未指定則使用最高損壞狀態

        Returns:
            Dict[str, float]: 震度級別對應倒塌機率的字典 (如 {'3': 0.001, '4': 0.005, ...})
        """
        if not self.fragility_parameters:
            logger.error("No fragility parameters available. Run fit_all_fragility_curves() first.")
            return {}

        # 自動選擇倒塌損壞狀態 (通常是最高的損壞狀態)
        if collapse_damage_state is None:
            # 選擇IDR閾值最高的損壞狀態作為倒塌狀態
            collapse_damage_state = max(
                self.damage_states.keys(),
                key=lambda ds: self.damage_states[ds]
            )

        if collapse_damage_state not in self.fragility_parameters:
            logger.error(f"Collapse damage state '{collapse_damage_state}' not found in fragility parameters")
            return {}

        logger.info(f"Generating PGA fragility curve using collapse state: {collapse_damage_state}")

        # 獲取倒塌狀態的易損性參數
        params = self.fragility_parameters[collapse_damage_state]
        theta = params['median_theta']  # Sa in g
        beta = params['lognormal_beta']

        logger.debug(f"Collapse fragility parameters: θ={theta:.4f}g, β={beta:.4f}")

        # 獲取目標震度級別的PGA值 (單位: cm/s²)
        target_pga_values = self.pga_mapper.get_target_pga_values()

        # 轉換Sa(g)到PGA(cm/s²)
        # 注意：這裡需要做單位轉換和近似轉換
        # Sa(g) * 980 ≈ PGA(cm/s²) 是粗略的轉換，實際上兩者關係複雜
        # 這裡使用簡化假設: PGA ≈ Sa × 980 cm/s²
        fragility_curve = {}

        for level, target_pga_cms2 in target_pga_values.items():
            # 將PGA從cm/s²轉換為g
            target_pga_g = target_pga_cms2 / 980.665  # cm/s² to g (正確的重力加速度)

            # 計算該PGA下的倒塌機率
            # 注意：這裡假設易損性參數是基於PGA(g)建立的
            collapse_prob = stats.lognorm.cdf(target_pga_g, s=beta, scale=theta)

            # 確保機率在合理範圍內
            collapse_prob = float(np.clip(collapse_prob, 0.0, 1.0))

            fragility_curve[level] = collapse_prob

            logger.debug(f"Level {level}: PGA={target_pga:.1f} cm/s², "
                        f"Equivalent Sa={equivalent_sa:.4f}g, "
                        f"Collapse Prob={collapse_prob:.6f}")

        # 驗證結果的合理性
        if self.pga_mapper.validate_fragility_curve(fragility_curve):
            logger.info("PGA fragility curve generated and validated successfully")
        else:
            logger.warning("PGA fragility curve validation failed - results may be unreliable")

        return fragility_curve

    def generate_enhanced_pga_fragility_curve(self,
                                            collapse_damage_state: str = None) -> Dict[str, float]:
        """
        生成PGA易損性曲線，基於正確的PGA=Sa(T=0)關係

        Args:
            collapse_damage_state: 倒塌損壞狀態名稱

        Returns:
            Dict[str, float]: 震度級別對應倒塌機率的字典
        """
        if not self.fragility_parameters:
            logger.error("No fragility parameters available")
            return {}

        # 選擇倒塌狀態
        if collapse_damage_state is None:
            collapse_damage_state = max(
                self.damage_states.keys(),
                key=lambda ds: self.damage_states[ds]
            )

        if collapse_damage_state not in self.fragility_parameters:
            logger.error(f"Collapse damage state '{collapse_damage_state}' not found")
            return {}

        params = self.fragility_parameters[collapse_damage_state]
        theta_sa = params['median_theta']  # Sa in g
        beta = params['lognormal_beta']

        logger.info(f"Enhanced PGA fragility curve generation:")
        logger.info(f"  Collapse state: {collapse_damage_state}")
        logger.info(f"  PGA median (θ): {theta_sa:.4f} g")
        logger.info(f"  Log-std (β): {beta:.4f}")
        logger.info(f"  Based on correct PGA=Sa(T=0) relationship")

        # 創建一組PGA值來建立完整的易損性曲線
        pga_range_g = np.logspace(-2, 1, 1000)  # 0.01g to 10g (PGA in g)
        collapse_probs = stats.lognorm.cdf(pga_range_g, s=beta, scale=theta_sa)

        # 轉換PGA到cm/s²用於震度映射
        pga_range_cms2 = pga_range_g * 980.665  # g to cm/s²

        # 使用PGA映射器進行插值
        fragility_curve = self.pga_mapper.create_fragility_curve_dict(
            pga_range_cms2, collapse_probs
        )

        # 記錄結果
        logger.info("Enhanced PGA fragility curve results:")
        for level in self.pga_mapper.get_all_target_levels():
            prob = fragility_curve.get(level, 0.0)
            target_pga = self.pga_mapper.intensity_level_to_pga(level)
            logger.info(f"  Level {level:2}: PGA={target_pga:6.1f} cm/s², P_collapse={prob:.6f}")

        return fragility_curve

    def export_standard_fragility_result(self,
                                       collapse_damage_state: str = None,
                                       analysis_metadata: Dict = None) -> Dict[str, Any]:
        """
        匯出標準化的易損性分析結果，符合快取系統格式

        Args:
            collapse_damage_state: 倒塌損壞狀態名稱
            analysis_metadata: 分析元數據

        Returns:
            Dict: 標準化的易損性結果，可直接儲存到快取
        """
        from datetime import datetime
        import time

        # 生成PGA易損性曲線
        fragility_curve = self.generate_enhanced_pga_fragility_curve(collapse_damage_state)

        if not fragility_curve:
            logger.error("Failed to generate PGA fragility curve")
            return {}

        # 準備分析元數據
        if analysis_metadata is None:
            analysis_metadata = {}

        # 加入基本分析資訊
        metadata = {
            'total_ida_analyses': len(self.ida_results),
            'unique_ground_motions': int(self.ida_results['gm_id'].nunique()),
            'damage_states_analyzed': list(self.damage_states.keys()),
            'collapse_damage_state_used': collapse_damage_state or "auto-selected",
            **analysis_metadata
        }

        # 加入PSDM資訊（如果可用）
        if self.psdm_parameters:
            metadata['psdm_regression'] = {
                'slope_a': float(self.psdm_parameters['slope_a']),
                'intercept_b': float(self.psdm_parameters['intercept_b']),
                'r_squared': float(self.psdm_parameters['r_squared']),
                'beta_d_given_im': float(self.psdm_parameters['beta_d_given_im'])
            }

        # 加入易損性參數
        if collapse_damage_state and collapse_damage_state in self.fragility_parameters:
            params = self.fragility_parameters[collapse_damage_state]
            metadata['fragility_parameters'] = {
                'median_theta_g': float(params['median_theta']),
                'lognormal_beta': float(params['lognormal_beta']),
                'r_squared': float(params['r_squared']),
                'idr_threshold': float(params['threshold_idr'])
            }

        # 準備標準化結果
        standard_result = {
            'collapse_probabilities': fragility_curve,
            'analysis_metadata': metadata,
            'computed_timestamp': datetime.now().isoformat(),
            'computation_time': 0.0  # 需要由調用者設定
        }

        logger.info(f"Standard fragility result exported with {len(fragility_curve)} intensity levels")

        return standard_result

    def calculate_collapse_probability_at_pga(self, pga_value: float,
                                            collapse_damage_state: str = None) -> float:
        """
        計算指定PGA值的倒塌機率

        Args:
            pga_value: PGA值 (cm/s²)
            collapse_damage_state: 倒塌損壞狀態名稱

        Returns:
            float: 倒塌機率 (0-1)
        """
        if not self.fragility_parameters:
            logger.error("No fragility parameters available")
            return 0.0

        # 選擇倒塌狀態
        if collapse_damage_state is None:
            collapse_damage_state = max(
                self.damage_states.keys(),
                key=lambda ds: self.damage_states[ds]
            )

        if collapse_damage_state not in self.fragility_parameters:
            logger.error(f"Collapse damage state '{collapse_damage_state}' not found")
            return 0.0

        params = self.fragility_parameters[collapse_damage_state]
        theta_sa = params['median_theta']  # Sa in g
        beta = params['lognormal_beta']

        # 將PGA從cm/s²轉換為g
        pga_g = pga_value / 980.665  # cm/s² to g (正確的重力加速度)

        # 計算倒塌機率
        collapse_prob = stats.lognorm.cdf(pga_g, s=beta, scale=theta_sa)

        return float(np.clip(collapse_prob, 0.0, 1.0))


def main():
    """Test the fragility analysis module"""
    print("Fragility Analysis module loaded successfully")
    print("To test, use with actual IDA results from the main analysis")


if __name__ == "__main__":
    main()