#!/usr/bin/env python3
"""
Main Function: Generate Fragility Curves using OpenSeesPy IDA
Complete implementation of the fragility curve generation system
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import all modules
from ground_motion_processor import GroundMotionProcessor
from structural_model import StickModel
from ida_engine import IDAEngine
from fragility_analysis import FragilityAnalyzer
from visualization import FragilityPlotter
from project_config import ProjectConfig

# Set up logging
def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('fragility_analysis.log')
        ]
    )

logger = logging.getLogger(__name__)


def generate_fragility_curves(
    building_id: str,
    model_properties: List[Dict],
    gm_directory: str,
    gm_list_file: str,
    output_directory: str,
    analysis_config: Dict,
    damping_ratio: float = 0.05
) -> None:
    """
    為指定的單一棟建築模型，執行完整的IDA分析並生成易損性曲線。

    這個高階函式封裝了從模型建立、批次動力分析到統計後處理的
    所有步驟。它會使用 OpenSeesPy 作為後端分析引擎。

    Args:
        building_id (str):
            建築模型的唯一識別符，用於命名輸出檔案 (例如：\"Typology_RC_5F_Pre99\")。

        model_properties (list[dict]):
            一個 Python 列表，其中每個字典定義了一層樓的結構特性。
            這是定義 Stick Model 的核心輸入。

            每個字典必須包含以下必要參數：
            - story (int): 樓層編號
            - mass (float): 樓層質量 (kgf·s²/cm)
            - k (float): 樓層剪力剛度 (kgf/cm)
            - Fy (float): 降伏強度 (kgf)
            - alpha (float): 硬化比 (0~1)

            可選參數：
            - material_type (str): 材料類型 ('steel' 或 'concrete')
            - story_height (float): 樓層高度 (cm)
            - E (float): 彈性模數 (kgf/cm²)

        gm_directory (str):
            存放所有地震波紀錄檔案 (.txt) 的資料夾路徑。

        gm_list_file (str):
            一個索引檔案的路徑，該檔案列出了所有要使用的地震波及其元數據 (dt)。

        output_directory (str):
            一個資料夾路徑，用於存放所有分析結果，包括原始數據、參數表與最終圖檔。
            如果資料夾不存在，函式會嘗試建立它。

        analysis_config (dict):
            一個字典，包含了IDA分析與損傷狀態的所有設定。

        damping_ratio (float, optional):
            結構的阻尼比，預設為 0.05 (5%)。

    Returns:
        None:
            這個函式沒有回傳值。它會將所有結果直接寫入指定的 output_directory 中。
    """

    # Setup logging
    setup_logging()
    logger.info(f"Starting fragility curve generation for building: {building_id}")

    start_time = time.time()

    
    # Step 1: Initialize project configuration
    logger.info("Step 1: Initializing project configuration...")
    config = ProjectConfig()
    config.setup_directories(building_id)

    # Validate inputs
    if not config.validate_inputs(gm_directory, gm_list_file):
        raise ValueError("Input validation failed")

    # Step 2: Initialize ground motion processor
    logger.info("Step 2: Processing ground motion data...")
    gm_processor = GroundMotionProcessor(gm_directory)

    # Scan and validate ground motions
    inventory = gm_processor.scan_ground_motions()
    if len(inventory) == 0:
        raise ValueError("No valid ground motion records found")

    logger.info(f"Found {len(inventory)} valid ground motion records")

    # Create or update GM list file
    if not Path(gm_list_file).exists():
        logger.info("Creating ground motion list file...")
        gm_processor.create_gm_list_file(gm_list_file)

    # Step 3: Build structural model
    logger.info("Step 3: Building structural model...")
    stick_model = StickModel(model_properties, damping_ratio)

    # Build the OpenSees model
    if not stick_model.build_model():
        raise RuntimeError("Failed to build structural model")

    # Perform eigenvalue analysis
    eigen_success, T1 = stick_model.perform_eigenvalue_analysis()
    if eigen_success:
        logger.info(f"Fundamental period: T1 = {T1:.4f} sec")
    else:
        logger.warning("Eigenvalue analysis failed, using estimated period")

    # Step 4: Run IDA analysis
    logger.info("Step 4: Running Incremental Dynamic Analysis...")
    ida_engine = IDAEngine(stick_model, gm_processor, analysis_config)

    # Run full IDA
    ida_results = ida_engine.run_full_ida()

    if ida_results.empty:
        raise RuntimeError("IDA analysis failed - no results obtained")

    logger.info(f"IDA analysis completed: {len(ida_results)} analyses")

    # Step 5: Statistical analysis and fragility curve fitting
    logger.info("Step 5: Fitting fragility curves...")
    fragility_analyzer = FragilityAnalyzer(ida_results, analysis_config['damage_states'])

    # Fit fragility curves
    fragility_params = fragility_analyzer.fit_all_fragility_curves()
    if not fragility_params:
        raise RuntimeError("Failed to fit fragility curves")

    # Generate curve points for plotting
    fragility_curves = fragility_analyzer.generate_fragility_curves()

    logger.info(f"Successfully fitted {len(fragility_params)} fragility curves")

    # Step 6: Create visualizations
    logger.info("Step 6: Creating visualizations...")
    plotter = FragilityPlotter()

    # Create comprehensive visualization report
    output_path = Path(output_directory)
    visualization_files = plotter.create_comprehensive_report(
        fragility_curves, ida_results, fragility_params, building_id, str(output_path)
    )

    # Step 7: Save results
    logger.info("Step 7: Saving analysis results...")

    # Save raw IDA results
    ida_output_file = output_path / f"{building_id}_IDA_Raw_Output.csv"
    ida_engine.save_results(str(ida_output_file))

    # Save fragility parameters
    params_output_file = output_path / f"{building_id}_FRG_Parameters.csv"
    fragility_analyzer.save_fragility_parameters(str(params_output_file))

    # Save PSDM regression parameters if available
    if hasattr(fragility_analyzer, 'psdm_parameters') and fragility_analyzer.psdm_parameters:
        psdm_output_file = output_path / f"{building_id}_PSDM_Parameters.csv"
        fragility_analyzer.save_psdm_parameters(str(psdm_output_file))

    # Save complete fragility curve data points
    curves_output_file = output_path / f"{building_id}_Fragility_Curves_Data.csv"
    fragility_analyzer.save_fragility_curves(str(curves_output_file), building_id=building_id)

    # Save analysis summary
    summary_file = output_path / f"{building_id}_Analysis_Summary.txt"
    with open(summary_file, 'w') as f:
        f.write(f"Fragility Curve Analysis Summary\n")
        f.write(f"Building ID: {building_id}\n")
        f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"=" * 50 + "\n\n")

        # Model summary
        f.write(stick_model.get_model_summary())
        f.write("\n" + "=" * 50 + "\n\n")

        # IDA summary
        ida_summary = ida_engine.get_analysis_summary()
        f.write("IDA Analysis Summary:\n")
        for key, value in ida_summary.items():
            f.write(f"  {key}: {value}\n")
        f.write("\n" + "=" * 50 + "\n\n")

        # Fragility summary
        f.write(fragility_analyzer.get_fragility_summary())

    # Step 8: Final report
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("FRAGILITY CURVE ANALYSIS COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info(f"Building ID: {building_id}")
    logger.info(f"Total elapsed time: {elapsed_time/60:.1f} minutes")
    logger.info(f"Output directory: {output_directory}")

    # List output files
    logger.info("Generated files:")
    output_files = [
        ida_output_file,
        params_output_file,
        curves_output_file,
        summary_file
    ] + [Path(f) for f in visualization_files]

    for file_path in output_files:
        if file_path.exists():
            logger.info(f"  ✓ {file_path.name}")
        else:
            logger.warning(f"  ✗ {file_path.name} (not found)")

    logger.info("Analysis completed successfully!")




def main():
    """Example usage of the generate_fragility_curves function"""

    # Example from PRD document
    if __name__ == "__main__":
        # 1. Define building to analyze
        building_name = "Typology_RC_5F_Pre99_Taipei"

        # 2. Define Stick Model properties (kgf-cm-sec system)
        # Units: mass (kgf·s²/cm), stiffness k (kgf/cm), yield strength Fy (kgf)
        #
        # NEW FEATURES in enhanced format:
        # - material_type: 'steel' or 'concrete' (affects elastic modulus E)
        # - story_height: individual story height in cm (default: 300)
        # - E: custom elastic modulus in kgf/cm² (optional, auto-set by material_type)
        five_story_model = [
            {'story': 1, 'mass': 120.0, 'k': 6.5e4, 'Fy': 4800.0, 'alpha': 0.025,
             'material_type': 'concrete', 'story_height': 400.0},
            {'story': 2, 'mass': 120.0, 'k': 6.5e4, 'Fy': 4800.0, 'alpha': 0.025,
             'material_type': 'concrete', 'story_height': 350.0},
            {'story': 3, 'mass': 120.0, 'k': 6.2e4, 'Fy': 4600.0, 'alpha': 0.025,
             'material_type': 'concrete', 'story_height': 350.0},
            {'story': 4, 'mass': 120.0, 'k': 6.2e4, 'Fy': 4600.0, 'alpha': 0.025,
             'material_type': 'concrete', 'story_height': 350.0},
            {'story': 5, 'mass': 130.0, 'k': 6.0e4, 'Fy': 4500.0, 'alpha': 0.025,
             'material_type': 'concrete', 'story_height': 350.0},
        ]

        # Example with steel structure and varying story heights
        three_story_steel_model = [
            {'story': 1, 'mass': 1000.0, 'k': 203944, 'Fy': 4800.0, 'alpha': 0.025,
             'material_type': 'steel', 'story_height': 450.0, 'E': 2.0e6},
            {'story': 2, 'mass': 1000.0, 'k': 203944, 'Fy': 4800.0, 'alpha': 0.025,
             'material_type': 'steel', 'story_height': 400.0, 'E': 2.0e6},
            {'story': 3, 'mass': 1000.0, 'k': 203944, 'Fy': 4500.0, 'alpha': 0.025,
             'material_type': 'steel', 'story_height': 400.0, 'E': 2.0e6},
        ]

        # Simple model using defaults (backward compatibility)
        three_story_simple_model = [
            {'story': 1, 'mass': 1000.0, 'k': 203944, 'Fy': 4800.0, 'alpha': 0.025},
            {'story': 2, 'mass': 1000.0, 'k': 203944, 'Fy': 4800.0, 'alpha': 0.025},
            {'story': 3, 'mass': 1000.0, 'k': 203944, 'Fy': 4500.0, 'alpha': 0.025},
        ]

        # three_story_simple_model = [
        #     {'story': 1, 'mass': 10.0, 'k': 203944, 'Fy': 4000000.0, 'alpha': 0.025},
        #     {'story': 2, 'mass': 10.0, 'k': 203944, 'Fy': 4000000.0, 'alpha': 0.025},
        #     {'story': 3, 'mass': 10.0, 'k': 203944, 'Fy': 4000000.0, 'alpha': 0.025},
        # ]

        # 3. & 4. Define ground motion paths
        gm_folder = "./ground_motions"
        gm_list = f"{gm_folder}/GM_List.csv"

        # 5. Define output path
        output_folder = f"./results/{building_name}"

        # 6. Define analysis configuration
        config_dict = {
            "pga_targets": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4,
                           0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0],
            # 支援舊的參數名稱以保持向後相容
            "im_levels_g": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4,
                           0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0],
            "damage_states": {
                'DS0_Slight_NSD': 0.002,
                'DS1_Slight_SD': 0.005,
                'DS2_Moderate_SD': 0.015,
                'DS3_Severe_SD': 0.025,
                'DS4_Collapse': 0.050
            },
            "max_drift_ratio": 0.10,
            "convergence_tolerance": 1e-6,
            "max_iterations": 100
        }

        # Choose model to analyze (you can change this)
        # Options: five_story_model, three_story_steel_model, three_story_simple_model
        selected_model = five_story_model  # Using simple model for backward compatibility

        # Update building name based on selected model
        if selected_model == five_story_model:
            building_name = "RC_5Story_Enhanced"
        elif selected_model == three_story_steel_model:
            building_name = "Steel_3Story_Enhanced"
        else:
            building_name = "Simple_3Story_Default"

        # Update output folder
        output_folder = f"./results/{building_name}"

        # Execute main function!
        try:
            generate_fragility_curves(
                building_id=building_name,
                model_properties=selected_model,
                gm_directory=gm_folder,
                gm_list_file=gm_list,
                output_directory=output_folder,
                analysis_config=config_dict,
                damping_ratio=0.05
            )

            print("\n" + "="*60)
            print("SUCCESS: Fragility curve analysis completed!")
            print("="*60)
            print(f"Check the results in: {output_folder}")

        except Exception as e:
            print(f"\nERROR: Analysis failed - {e}")
            print("Check the log file for detailed error information")
            sys.exit(1)


if __name__ == "__main__":
    main()