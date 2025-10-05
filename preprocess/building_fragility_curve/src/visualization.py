#!/usr/bin/env python3
"""
Visualization Module for Fragility Curves
Professional plotting and visualization of fragility analysis results
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import LogFormatter, LogLocator
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FragilityPlotter:
    """
    Professional fragility curve visualization
    """

    def __init__(self, figsize: Tuple[float, float] = (12, 8)):
        """
        Initialize the fragility plotter

        Args:
            figsize (Tuple[float, float]): Figure size (width, height) in inches
        """
        self.figsize = figsize
        self.colors = {
            'DS0_Slight_NSD': '#2E8B57',      # Sea green
            'DS1_Slight_SD': '#4169E1',       # Royal blue
            'DS2_Moderate_SD': '#FF8C00',     # Dark orange
            'DS3_Severe_SD': '#DC143C',       # Crimson
            'DS4_Collapse': '#8B0000'         # Dark red
        }
        self.linestyles = ['-', '--', '-.', ':', '-']
        self.linewidth = 2.5

        # Set matplotlib style
        plt.style.use('default')
        self._setup_plotting_style()

    def _setup_plotting_style(self):
        """Setup professional plotting style"""
        plt.rcParams.update({
            'font.size': 12,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 11,
            'figure.titlesize': 16,
            'lines.linewidth': self.linewidth,
            'grid.alpha': 0.3,
            'axes.grid': True,
            'axes.axisbelow': True
        })

    def plot_fragility_curves(self, fragility_curves: Dict[str, pd.DataFrame],
                             building_id: str,
                             output_file: Optional[str] = None) -> plt.Figure:
        """
        Plot fragility curves for all damage states

        Args:
            fragility_curves (Dict[str, pd.DataFrame]): Fragility curve data
            building_id (str): Building identifier for title
            output_file (str, optional): Output file path

        Returns:
            plt.Figure: Matplotlib figure object
        """
        logger.info("Creating fragility curve plot...")

        fig, ax = plt.subplots(figsize=self.figsize)

        # Sort damage states by their typical severity order
        ds_order = ['DS0_Slight_NSD', 'DS1_Slight_SD', 'DS2_Moderate_SD', 'DS3_Severe_SD', 'DS4_Collapse']
        available_ds = [ds for ds in ds_order if ds in fragility_curves]

        # Plot each damage state curve
        for i, ds_name in enumerate(available_ds):
            curve_df = fragility_curves[ds_name]

            color = self.colors.get(ds_name, f'C{i}')
            linestyle = self.linestyles[i % len(self.linestyles)]

            # Clean display name
            display_name = self._format_damage_state_name(ds_name)

            ax.semilogx(curve_df['sa_g'], curve_df['probability'],
                       color=color, linestyle=linestyle, linewidth=self.linewidth,
                       label=display_name, marker='', markersize=0)

        # Customize plot
        ax.set_xlabel('Spectral Acceleration, Sa(T₁) [g]', fontweight='bold')
        ax.set_ylabel('Probability of Exceedance', fontweight='bold')
        ax.set_title(f'Fragility Curves - {building_id}', fontweight='bold', fontsize=14)

        # Set axis limits and scale
        ax.set_xlim(0.01, 3.0)
        ax.set_ylim(0, 1.0)

        # Add grid
        ax.grid(True, which='both', alpha=0.3)
        ax.grid(True, which='minor', alpha=0.15)

        # Add legend
        ax.legend(loc='lower right', frameon=True, fancybox=True, shadow=True)

        # Format x-axis ticks
        ax.set_xticks([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0])
        ax.set_xticklabels(['0.01', '0.02', '0.05', '0.1', '0.2', '0.5', '1.0', '2.0'])

        # Format y-axis ticks
        ax.set_yticks(np.arange(0, 1.1, 0.1))

        # Add annotation with analysis info
        self._add_analysis_annotation(ax, len(fragility_curves))

        plt.tight_layout()

        # Save if output file is specified
        if output_file:
            fig.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
            logger.info(f"Fragility curve plot saved to: {output_file}")

        return fig

    def plot_ida_results(self, ida_results: pd.DataFrame,
                        building_id: str,
                        output_file: Optional[str] = None) -> plt.Figure:
        """
        Plot IDA results (Sa vs Max IDR)

        Args:
            ida_results (pd.DataFrame): IDA analysis results
            building_id (str): Building identifier
            output_file (str, optional): Output file path

        Returns:
            plt.Figure: Matplotlib figure object
        """
        logger.info("Creating IDA results plot...")

        fig, ax = plt.subplots(figsize=self.figsize)

        # Separate successful and collapsed analyses
        successful = ida_results[ida_results['analysis_success'] == True]
        collapsed = ida_results[ida_results['collapse'] == True]

        # Support both old and new column names
        intensity_col = 'pga_target' if 'pga_target' in ida_results.columns else 'sa_target'
        intensity_label = 'Peak Ground Acceleration, PGA [g]' if intensity_col == 'pga_target' else 'Spectral Acceleration, Sa(T₁) [g]'

        # Plot successful analyses
        if len(successful) > 0:
            ax.scatter(successful[intensity_col], successful['max_idr'] * 100,  # Convert to percentage
                      c='blue', alpha=0.6, s=20, label='Analysis Successful')

        # Plot collapsed analyses
        if len(collapsed) > 0:
            ax.scatter(collapsed[intensity_col], collapsed['max_idr'] * 100,
                      c='red', alpha=0.8, s=30, marker='x', label='Analysis Collapsed')

        # Customize plot
        ax.set_xlabel(intensity_label, fontweight='bold')
        ax.set_ylabel('Maximum Interstory Drift Ratio [%]', fontweight='bold')
        ax.set_title(f'IDA Results - {building_id}', fontweight='bold', fontsize=14)

        # Set logarithmic scale for both axes
        ax.set_xscale('log')
        ax.set_yscale('log')

        # Set axis limits
        ax.set_xlim(0.01, 3.0)
        ax.set_ylim(0.01, 20)  # 0.01% to 20%

        # Add grid
        ax.grid(True, which='both', alpha=0.3)

        # Add legend
        ax.legend(loc='lower right')

        # Add horizontal lines for damage state thresholds
        damage_thresholds = [0.2, 0.5, 1.5, 2.5, 5.0]  # Typical thresholds in %
        threshold_labels = ['DS0', 'DS1', 'DS2', 'DS3', 'DS4']

        for threshold, label in zip(damage_thresholds, threshold_labels):
            ax.axhline(y=threshold, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            ax.text(2.5, threshold, label, fontsize=9, alpha=0.7)

        plt.tight_layout()

        # Save if output file is specified
        if output_file:
            fig.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
            logger.info(f"IDA results plot saved to: {output_file}")

        return fig

    def plot_fragility_parameters_summary(self, fragility_parameters: Dict[str, Dict],
                                         building_id: str,
                                         output_file: Optional[str] = None) -> plt.Figure:
        """
        Create summary plot of fragility parameters

        Args:
            fragility_parameters (Dict[str, Dict]): Fragility parameters
            building_id (str): Building identifier
            output_file (str, optional): Output file path

        Returns:
            plt.Figure: Matplotlib figure object
        """
        logger.info("Creating fragility parameters summary plot...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Extract data
        ds_names = []
        medians = []
        betas = []
        thresholds = []

        for ds_name, params in fragility_parameters.items():
            ds_names.append(self._format_damage_state_name(ds_name))
            medians.append(params['median_theta'])
            betas.append(params['lognormal_beta'])
            thresholds.append(params['threshold_idr'] * 100)  # Convert to percentage

        # Plot 1: Median vs Beta
        colors = [self.colors.get(ds, 'gray') for ds in fragility_parameters.keys()]

        scatter = ax1.scatter(medians, betas, c=colors, s=100, alpha=0.7, edgecolors='black')

        for i, name in enumerate(ds_names):
            ax1.annotate(name, (medians[i], betas[i]),
                        xytext=(5, 5), textcoords='offset points', fontsize=10)

        ax1.set_xlabel('Median θ [g]', fontweight='bold')
        ax1.set_ylabel('Lognormal Standard Deviation β', fontweight='bold')
        ax1.set_title('Fragility Parameters', fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # Plot 2: IDR Thresholds
        bars = ax2.bar(range(len(ds_names)), thresholds, color=colors, alpha=0.7, edgecolor='black')

        ax2.set_xlabel('Damage State', fontweight='bold')
        ax2.set_ylabel('IDR Threshold [%]', fontweight='bold')
        ax2.set_title('Damage State Thresholds', fontweight='bold')
        ax2.set_xticks(range(len(ds_names)))
        ax2.set_xticklabels(ds_names, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar, threshold in zip(bars, thresholds):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                    f'{threshold:.1f}%', ha='center', va='bottom', fontsize=10)

        plt.suptitle(f'Fragility Analysis Summary - {building_id}', fontweight='bold', fontsize=16)
        plt.tight_layout()

        # Save if output file is specified
        if output_file:
            fig.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
            logger.info(f"Parameters summary plot saved to: {output_file}")

        return fig

    def _format_damage_state_name(self, ds_name: str) -> str:
        """
        Format damage state name for display

        Args:
            ds_name (str): Raw damage state name

        Returns:
            str: Formatted name
        """
        name_mapping = {
            'DS0_Slight_NSD': 'DS0: Slight Non-Structural',
            'DS1_Slight_SD': 'DS1: Slight Structural',
            'DS2_Moderate_SD': 'DS2: Moderate Structural',
            'DS3_Severe_SD': 'DS3: Severe Structural',
            'DS4_Collapse': 'DS4: Collapse'
        }

        return name_mapping.get(ds_name, ds_name)

    def _add_analysis_annotation(self, ax, n_curves: int):
        """
        Add analysis information annotation

        Args:
            ax: Matplotlib axes object
            n_curves (int): Number of curves plotted
        """
        info_text = f'Analysis Type: Incremental Dynamic Analysis (IDA)\n'
        info_text += f'Curve Fitting: Lognormal Distribution\n'
        info_text += f'Number of Damage States: {n_curves}'

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    def create_comprehensive_report(self, fragility_curves: Dict[str, pd.DataFrame],
                                  ida_results: pd.DataFrame,
                                  fragility_parameters: Dict[str, Dict],
                                  building_id: str,
                                  output_dir: str) -> List[str]:
        """
        Create comprehensive visualization report

        Args:
            fragility_curves (Dict[str, pd.DataFrame]): Fragility curve data
            ida_results (pd.DataFrame): IDA results
            fragility_parameters (Dict[str, Dict]): Fragility parameters
            building_id (str): Building identifier
            output_dir (str): Output directory

        Returns:
            List[str]: List of created file paths
        """
        logger.info("Creating comprehensive visualization report...")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []

        # 1. Main fragility curves plot
        fragility_file = output_dir / f"{building_id}_Fragility_Curves.png"
        self.plot_fragility_curves(fragility_curves, building_id, str(fragility_file))
        created_files.append(str(fragility_file))

        # 2. IDA results plot
        ida_file = output_dir / f"{building_id}_IDA_Results.png"
        self.plot_ida_results(ida_results, building_id, str(ida_file))
        created_files.append(str(ida_file))

        # 3. Parameters summary plot
        params_file = output_dir / f"{building_id}_Parameters_Summary.png"
        self.plot_fragility_parameters_summary(fragility_parameters, building_id, str(params_file))
        created_files.append(str(params_file))

        logger.info(f"Comprehensive report created: {len(created_files)} files in {output_dir}")

        return created_files


def main():
    """Test the visualization module with sample data"""
    print("Visualization module loaded successfully")

    # Create sample data for testing
    plotter = FragilityPlotter()

    # Sample fragility curve data
    sa_values = np.logspace(-2, 0.5, 50)
    sample_curves = {}

    # Create sample curves with different parameters
    damage_states = ['DS0_Slight_NSD', 'DS1_Slight_SD', 'DS2_Moderate_SD', 'DS3_Severe_SD', 'DS4_Collapse']
    medians = [0.15, 0.25, 0.45, 0.75, 1.2]
    betas = [0.4, 0.45, 0.5, 0.55, 0.6]

    for ds, median, beta in zip(damage_states, medians, betas):
        from scipy import stats
        probabilities = stats.lognorm.cdf(sa_values, s=beta, scale=median)
        sample_curves[ds] = pd.DataFrame({
            'sa_g': sa_values,
            'probability': probabilities,
            'damage_state': ds
        })

    # Create test plot
    fig = plotter.plot_fragility_curves(sample_curves, "Test_Building_5F", "test_fragility_curves.png")
    plt.show()

    print("Test plot created successfully")


if __name__ == "__main__":
    main()