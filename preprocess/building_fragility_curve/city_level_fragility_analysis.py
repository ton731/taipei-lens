#!/usr/bin/env python3
"""
City-Level Fragility Analysis Main Program

城市級建築易損性分析主程序

整合所有分析模組，提供完整的從建築分類到易損性曲線生成的工作流程。
支援大規模並行處理、自動快取管理、進度追蹤和結果驗證。

使用方式:
    python city_level_fragility_analysis.py --geojson building_data.geojson
                                           --gm-dir ground_motions/
                                           --gm-list ground_motions.txt
                                           --output-dir results/
                                           --workers 8
"""

import argparse
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import all required modules
from geojson_processor import GeoJSONProcessor
from parallel_processor import ParallelFragilityProcessor
from result_validator import FragilityCurveValidator, ArchetypeConsistencyValidator
from utils.progress_tracker import DetailedProgressTracker, setup_comprehensive_logging
from fragility_cache import FragilityCacheManager

logger = logging.getLogger(__name__)


class CityLevelFragilityAnalysis:
    """
    城市級易損性分析主控制器

    整合所有分析組件，提供統一的分析介面
    """

    def __init__(self,
                 geojson_file: str,
                 gm_directory: str,
                 gm_list_file: str,
                 output_directory: str,
                 max_workers: int = None,
                 cache_file: str = None,
                 analysis_config: Dict = None):
        """
        初始化城市級分析系統

        Args:
            geojson_file: 建築GeoJSON檔案路徑
            gm_directory: 地震波目錄
            gm_list_file: 地震波清單檔案
            output_directory: 輸出目錄
            max_workers: 最大並行工作程序數
            cache_file: 快取檔案路徑
            analysis_config: 分析配置
        """
        # 檔案路徑設定
        self.geojson_file = Path(geojson_file)
        self.gm_directory = Path(gm_directory)
        self.gm_list_file = Path(gm_list_file)
        self.output_directory = Path(output_directory)

        # 建立輸出目錄
        self.output_directory.mkdir(parents=True, exist_ok=True)

        # 設定快取檔案
        if cache_file is None:
            cache_file = self.output_directory / "fragility_cache.json"
        self.cache_file = Path(cache_file)

        # 分析配置
        self.analysis_config = analysis_config or self._get_default_config()
        self.max_workers = max_workers

        # 初始化核心模組
        self.geojson_processor = GeoJSONProcessor(
            str(self.geojson_file),
            chunk_size=1000,
            backup_original=True
        )

        self.parallel_processor = ParallelFragilityProcessor(
            max_workers=self.max_workers,
            gm_directory=str(self.gm_directory),
            gm_list_file=str(self.gm_list_file),
            cache_file=str(self.cache_file),
            analysis_config=self.analysis_config
        )

        # 驗證器
        self.fragility_validator = FragilityCurveValidator()
        self.consistency_validator = ArchetypeConsistencyValidator()

        # 統計資訊
        self.analysis_stats = {
            'start_time': None,
            'end_time': None,
            'total_duration_hours': 0.0,
            'buildings_processed': 0,
            'successful_analyses': 0,
            'cache_hits': 0,
            'validation_quality_score': 0.0
        }

        logger.info(f"City-Level Fragility Analysis initialized")
        logger.info(f"Input GeoJSON: {self.geojson_file}")
        logger.info(f"Ground motions: {self.gm_directory}")
        logger.info(f"Output directory: {self.output_directory}")
        logger.info(f"Max workers: {self.max_workers or 'auto'}")

    def _get_default_config(self) -> Dict:
        """獲取預設分析配置"""
        return {
            'damping_ratio': 0.05,
            'analysis_type': 'IDA',
            'pga_targets': [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],
            # 支援舊的參數名稱以保持向後相容
            'sa_targets': [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],
            'damage_states': {
                'Slight': 0.005,      # 0.5% IDR
                'Moderate': 0.015,    # 1.5% IDR
                'Extensive': 0.035,   # 3.5% IDR
                'Complete': 0.080,    # 8.0% IDR (collapse)
            },
            'max_analysis_time': 3600,  # 1 hour per building
            'retry_failed': False
        }

    def validate_inputs(self) -> bool:
        """
        驗證輸入檔案和參數

        Returns:
            bool: 驗證是否通過
        """
        logger.info("Validating input files and parameters...")

        validation_errors = []

        # 檢查GeoJSON檔案
        if not self.geojson_file.exists():
            validation_errors.append(f"GeoJSON file not found: {self.geojson_file}")

        # 檢查地震波目錄
        if not self.gm_directory.exists():
            validation_errors.append(f"Ground motion directory not found: {self.gm_directory}")

        # 檢查地震波清單
        if not self.gm_list_file.exists():
            validation_errors.append(f"Ground motion list file not found: {self.gm_list_file}")

        # 檢查GeoJSON格式
        if self.geojson_file.exists():
            try:
                validation_result = self.geojson_processor.validate_geojson_integrity()
                if not validation_result['valid_geojson']:
                    validation_errors.extend(validation_result['validation_errors'])
                else:
                    logger.info(f"GeoJSON validation passed: {validation_result['feature_count']} features")
            except Exception as e:
                validation_errors.append(f"GeoJSON validation error: {e}")

        # 檢查地震波檔案
        if self.gm_directory.exists():
            try:
                gm_files = list(self.gm_directory.glob("**/*.txt"))
                if len(gm_files) < 10:
                    logger.warning(f"Only {len(gm_files)} ground motion files found")
                else:
                    logger.info(f"Found {len(gm_files)} ground motion files")
            except Exception as e:
                validation_errors.append(f"Ground motion directory access error: {e}")

        if validation_errors:
            logger.error("Input validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False

        logger.info("Input validation passed")
        return True

    def _finalize_cache(self) -> Dict[str, Any]:
        """
        最終化 cache 檔案，確保所有結果都被保存

        Returns:
            Dict: Cache 狀態資訊
        """
        cache_status = {
            'cache_file_exists': False,
            'cache_file_path': str(self.cache_file),
            'cache_entries': 0,
            'cache_file_size_mb': 0.0,
            'finalization_success': False
        }

        try:
            # 檢查 cache 檔案是否存在
            if self.cache_file.exists():
                cache_status['cache_file_exists'] = True

                # 載入並檢查 cache 內容
                cache_manager = FragilityCacheManager(str(self.cache_file))
                cache_stats = cache_manager.get_cache_statistics()

                cache_status.update({
                    'cache_entries': cache_stats.total_entries,
                    'cache_file_size_mb': cache_stats.cache_file_size_mb,
                    'cache_hit_rate': cache_stats.hit_rate,
                    'total_requests': cache_stats.total_requests
                })

                # 強制最終保存以確保所有資料都寫入
                cache_manager.save_cache()
                logger.info(f"Final cache save completed: {cache_stats.total_entries} entries, "
                           f"{cache_stats.cache_file_size_mb:.2f} MB")

                cache_status['finalization_success'] = True

            else:
                logger.warning(f"Cache file not found at: {self.cache_file}")
                logger.info("This may indicate no fragility curves were computed or saved")

        except Exception as e:
            logger.error(f"Cache finalization failed: {e}")
            cache_status['error'] = str(e)

        return cache_status

    def run_complete_analysis(self,
                            max_buildings: Optional[int] = None,
                            skip_validation: bool = False) -> Dict[str, Any]:
        """
        執行完整的城市級易損性分析

        Args:
            max_buildings: 最大處理建築數量，None表示處理所有
            skip_validation: 是否跳過結果驗證

        Returns:
            Dict: 分析結果摘要
        """
        logger.info("="*60)
        logger.info("STARTING CITY-LEVEL FRAGILITY ANALYSIS")
        logger.info("="*60)

        self.analysis_stats['start_time'] = time.time()

        try:
            # 步驟1: 輸入驗證
            if not self.validate_inputs():
                raise RuntimeError("Input validation failed")

            # 步驟2: 建築分類
            logger.info("\n" + "="*40)
            logger.info("STEP 1: BUILDING CLASSIFICATION")
            logger.info("="*40)

            classified_buildings = self.geojson_processor.classify_buildings_batch(
                max_buildings=max_buildings
            )

            if not classified_buildings:
                raise RuntimeError("No buildings could be classified")

            logger.info(f"Successfully classified {len(classified_buildings)} buildings")

            # 統計建築原型
            archetype_stats = self.geojson_processor.get_archetype_statistics(classified_buildings)
            logger.info(f"Found {archetype_stats.get('unique_archetypes', 0)} unique archetypes")

            # 獲取年齡填補統計
            age_stats = self.geojson_processor.building_classifier.get_age_statistics()
            logger.info(f"Age filling summary: {age_stats['used_max_age']:,} from max_age, "
                       f"{age_stats['used_polygon_max_age']:,} from polygons, "
                       f"{age_stats['used_default_age']:,} from default PRE-1999")

            # 步驟3: 平行易損性分析
            logger.info("\n" + "="*40)
            logger.info("STEP 2: PARALLEL FRAGILITY ANALYSIS")
            logger.info("="*40)

            # 設定進度追蹤
            progress_tracker = DetailedProgressTracker(
                total_tasks=len(classified_buildings),
                report_interval=60.0,  # 每分鐘報告
                log_file=str(self.output_directory / "progress.json")
            )

            def progress_callback(progress_report: str):
                logger.info(f"Analysis Progress:\n{progress_report}")

            progress_tracker.add_progress_callback(progress_callback)

            # 執行平行分析
            fragility_results = self.parallel_processor.process_buildings_parallel(
                classified_buildings,
                progress_callback=progress_callback,
                report_interval=60.0
            )

            logger.info(f"Fragility analysis completed: {len(fragility_results)} results")

            # 更新統計
            processing_stats = self.parallel_processor.get_processing_statistics()
            self.analysis_stats.update({
                'buildings_processed': processing_stats.get('total_tasks', 0),
                'successful_analyses': processing_stats.get('successful_tasks', 0),
                'cache_hits': processing_stats.get('cache_hits', 0)
            })

            # 步驟3.5: 確保 Cache 最終保存和狀態檢查
            logger.info("\n" + "="*40)
            logger.info("STEP 2.5: CACHE FINALIZATION")
            logger.info("="*40)

            cache_status = self._finalize_cache()
            logger.info(f"Cache finalization completed: {cache_status}")

            # 步驟4: 結果驗證
            if not skip_validation:
                logger.info("\n" + "="*40)
                logger.info("STEP 3: RESULT VALIDATION")
                logger.info("="*40)

                quality_metrics = self.fragility_validator.validate_batch_results(fragility_results)
                self.analysis_stats['validation_quality_score'] = quality_metrics.quality_score

                logger.info(f"Validation completed - Quality Score: {quality_metrics.quality_score:.2%}")

                # 生成驗證報告
                validation_report_file = self.output_directory / "validation_report.json"
                self.fragility_validator.generate_validation_report(
                    quality_metrics, str(validation_report_file)
                )

            # 步驟5: 寫入結果到GeoJSON
            logger.info("\n" + "="*40)
            logger.info("STEP 4: WRITING RESULTS TO GEOJSON")
            logger.info("="*40)

            output_geojson = self.output_directory / "building_data_with_fragility.geojson"
            success = self.geojson_processor.write_fragility_results_to_geojson(
                fragility_results, str(output_geojson)
            )

            if not success:
                logger.error("Failed to write results to GeoJSON")

            # 步驟6: 最終驗證輸出檔案
            if success:
                final_validation = self.geojson_processor.validate_geojson_integrity(str(output_geojson))
                logger.info(f"Final output validation: {final_validation['features_with_fragility']} "
                           f"buildings with fragility curves")

            # 生成最終報告
            final_summary = self._generate_final_summary(
                classified_buildings, fragility_results, archetype_stats, cache_status
            )

            # 儲存最終報告
            summary_file = self.output_directory / "analysis_summary.json"
            self._save_analysis_summary(final_summary, str(summary_file))

            logger.info("\n" + "="*60)
            logger.info("CITY-LEVEL FRAGILITY ANALYSIS COMPLETED")
            logger.info("="*60)
            logger.info(self._format_final_summary(final_summary))

            return final_summary

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise

        finally:
            # 記錄結束時間
            self.analysis_stats['end_time'] = time.time()
            if self.analysis_stats['start_time']:
                duration = self.analysis_stats['end_time'] - self.analysis_stats['start_time']
                self.analysis_stats['total_duration_hours'] = duration / 3600

    def _generate_final_summary(self,
                              classified_buildings: List,
                              fragility_results: Dict,
                              archetype_stats: Dict,
                              cache_status: Dict = None) -> Dict[str, Any]:
        """生成最終分析摘要"""
        successful_results = sum(1 for r in fragility_results.values() if r is not None)
        failed_results = len(fragility_results) - successful_results

        # 獲取年齡填補統計
        age_stats = self.geojson_processor.building_classifier.get_age_statistics()

        summary = {
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'duration_hours': self.analysis_stats['total_duration_hours'],
                'analysis_config': self.analysis_config,
                'max_workers': self.max_workers,
                'cache_file': str(self.cache_file)
            },
            'input_summary': {
                'geojson_file': str(self.geojson_file),
                'ground_motion_directory': str(self.gm_directory),
                'ground_motion_list': str(self.gm_list_file)
            },
            'building_classification': {
                'total_buildings': len(classified_buildings),
                'classification_success_rate': len(classified_buildings) / self.analysis_stats.get('buildings_processed', 1),
                'unique_archetypes': archetype_stats.get('unique_archetypes', 0),
                'archetype_distribution': archetype_stats.get('archetype_distribution', {}),
                'age_filling_statistics': age_stats
            },
            'fragility_analysis': {
                'buildings_analyzed': len(fragility_results),
                'successful_analyses': successful_results,
                'failed_analyses': failed_results,
                'success_rate': successful_results / len(fragility_results) if fragility_results else 0,
                'cache_hit_rate': self.analysis_stats.get('cache_hits', 0) / len(fragility_results) if fragility_results else 0,
                'processing_statistics': self.parallel_processor.get_processing_statistics()
            },
            'quality_assessment': {
                'validation_quality_score': self.analysis_stats.get('validation_quality_score', 0.0),
                'validation_statistics': self.fragility_validator.get_validation_statistics()
            },
            'cache_management': cache_status or {
                'cache_file_exists': False,
                'cache_file_path': str(self.cache_file),
                'cache_entries': 0,
                'note': 'Cache status not available'
            },
            'output_files': {
                'fragility_geojson': str(self.output_directory / "building_data_with_fragility.geojson"),
                'validation_report': str(self.output_directory / "validation_report.json"),
                'progress_log': str(self.output_directory / "progress.json"),
                'analysis_summary': str(self.output_directory / "analysis_summary.json"),
                'cache_file': str(self.cache_file)
            }
        }

        return summary

    def _save_analysis_summary(self, summary: Dict, output_file: str) -> None:
        """儲存分析摘要"""
        try:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis summary saved: {output_file}")
        except Exception as e:
            logger.error(f"Failed to save analysis summary: {e}")

    def _format_final_summary(self, summary: Dict) -> str:
        """格式化最終摘要"""
        cache_info = summary.get('cache_management', {})
        cache_status_text = "✓ Available" if cache_info.get('cache_file_exists') else "✗ Not found"

        report = f"""
Final Analysis Summary:
  Duration: {summary['analysis_metadata']['duration_hours']:.1f} hours
  Buildings processed: {summary['building_classification']['total_buildings']}
  Unique archetypes: {summary['building_classification']['unique_archetypes']}
  Analysis success rate: {summary['fragility_analysis']['success_rate']:.1%}
  Cache hit rate: {summary['fragility_analysis']['cache_hit_rate']:.1%}
  Quality score: {summary['quality_assessment']['validation_quality_score']:.1%}

Cache Management:
  Cache file status: {cache_status_text}
  Cache entries: {cache_info.get('cache_entries', 0)}
  Cache file size: {cache_info.get('cache_file_size_mb', 0.0):.2f} MB
  Cache file path: {cache_info.get('cache_file_path', 'N/A')}

Output files saved to: {self.output_directory}
"""
        return report


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="City-Level Building Fragility Analysis",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--geojson',
        required=True,
        help='Input building GeoJSON file'
    )

    parser.add_argument(
        '--gm-dir',
        required=True,
        help='Ground motion files directory'
    )

    parser.add_argument(
        '--gm-list',
        required=True,
        help='Ground motion list file'
    )

    parser.add_argument(
        '--output-dir',
        default='./results',
        help='Output directory for results'
    )

    parser.add_argument(
        '--workers',
        type=int,
        help='Maximum number of parallel workers (default: CPU cores - 1)'
    )

    parser.add_argument(
        '--cache-file',
        help='Fragility curve cache file path'
    )

    parser.add_argument(
        '--max-buildings',
        type=int,
        help='Maximum number of buildings to process (for testing)'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip result validation step'
    )

    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    parser.add_argument(
        '--log-dir',
        default='./logs',
        help='Log files directory'
    )

    args = parser.parse_args()

    # 設定日誌系統
    setup_comprehensive_logging(
        log_dir=args.log_dir,
        log_level=args.log_level,
        max_log_files=10
    )

    logger.info("Starting City-Level Fragility Analysis")
    logger.info(f"Arguments: {vars(args)}")

    try:
        # 建立分析系統
        analysis_system = CityLevelFragilityAnalysis(
            geojson_file=args.geojson,
            gm_directory=args.gm_dir,
            gm_list_file=args.gm_list,
            output_directory=args.output_dir,
            max_workers=args.workers,
            cache_file=args.cache_file
        )

        # 執行完整分析
        final_summary = analysis_system.run_complete_analysis(
            max_buildings=args.max_buildings,
            skip_validation=args.skip_validation
        )

        logger.info("Analysis completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())