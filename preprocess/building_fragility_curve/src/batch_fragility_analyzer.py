#!/usr/bin/env python3
"""
Batch Fragility Analyzer Module

此模組提供批量易損性分析功能，支援大規模建築原型的易損性曲線生成。
整合了建築分類、參數生成、快取管理和PGA強度對應。

主要功能：
1. 批量建築原型分析
2. 自動快取管理
3. 標準化PGA易損性曲線輸出
4. 進度追蹤和錯誤處理
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import required modules
from building_classifier import BuildingProperties
from archetype_generator import ArchetypeParameterGenerator
from fragility_cache import FragilityCacheManager, FragilityCurveResult
from fragility_analysis import FragilityAnalyzer

# Import existing analysis modules
sys.path.append(str(Path(__file__).parent.parent))
from ground_motion_processor import GroundMotionProcessor
from structural_model import StickModel
from ida_engine import IDAEngine
from project_config import ProjectConfig

logger = logging.getLogger(__name__)


class BatchFragilityAnalyzer:
    """
    批量易損性分析器

    整合所有必要的模組，提供從建築分類到易損性曲線生成的完整流程
    """

    def __init__(self,
                 gm_directory: str,
                 gm_list_file: str,
                 cache_file: str = "fragility_cache.json",
                 analysis_config: Dict = None,
                 worker_id: Optional[str] = None):
        """
        初始化批量易損性分析器

        Args:
            gm_directory: 地震波檔案目錄
            gm_list_file: 地震波清單檔案
            cache_file: 快取檔案路徑
            analysis_config: 分析配置
            worker_id: Worker ID，用於多進程環境
        """
        self.gm_directory = Path(gm_directory)
        self.gm_list_file = Path(gm_list_file)
        self.worker_id = worker_id

        # 初始化核心模組
        self.archetype_generator = ArchetypeParameterGenerator()
        self.cache_manager = FragilityCacheManager(cache_file, worker_id=worker_id)

        # 地震波處理器（延遲初始化）
        self._gm_processor = None

        # 預設分析配置
        self.analysis_config = analysis_config or self._get_default_analysis_config()

        # 統計資訊
        self.analysis_stats = {
            'total_requested': 0,
            'cache_hits': 0,
            'main_cache_hits': 0,     # 新增：主cache命中次數
            'worker_cache_hits': 0,   # 新增：worker cache命中次數
            'new_analyses': 0,
            'failed_analyses': 0,
            'total_computation_time': 0.0
        }

        # 追蹤是否有新的計算結果需要保存
        self.has_new_results = False

        logger.info(f"Batch Fragility Analyzer initialized")
        logger.info(f"Ground motions: {self.gm_directory}")
        logger.info(f"Cache file: {cache_file}")

    @property
    def gm_processor(self) -> GroundMotionProcessor:
        """延遲初始化地震波處理器"""
        if self._gm_processor is None:
            self._gm_processor = GroundMotionProcessor(
                str(self.gm_directory),
                str(self.gm_list_file)
            )
        return self._gm_processor

    def _check_main_cache(self, archetype_code: str) -> Optional[FragilityCurveResult]:
        """
        檢查主cache檔案是否已有指定archetype的分析結果

        Args:
            archetype_code: 建築原型編碼

        Returns:
            FragilityCurveResult: 如果主cache中存在則返回結果，否則返回None
        """
        try:
            # 創建主cache管理器實例（worker_id=None表示主cache）
            main_cache_path = str(Path(self.cache_manager.cache_file_path).parent / "fragility_cache.json")
            main_cache_manager = FragilityCacheManager(main_cache_path, worker_id=None)

            # 查詢主cache
            result = main_cache_manager.get_fragility_curve(archetype_code, check_updates=True)

            if result is not None:
                logger.info(f"Main cache HIT for {archetype_code} - using existing result")
                return result
            else:
                logger.debug(f"Main cache MISS for {archetype_code} - will perform new analysis")
                return None

        except Exception as e:
            logger.warning(f"Failed to check main cache for {archetype_code}: {e}")
            return None

    def _get_default_analysis_config(self) -> Dict:
        """獲取預設分析配置"""
        return {
            'damping_ratio': 0.05,
            'analysis_type': 'IDA',
            'pga_targets': [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],  # PGA in g
            # 支援舊的參數名稱以保持向後相容
            'sa_targets': [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],  # 舊名稱，現在代表PGA
            'damage_states': {
                'Slight': 0.005,      # 0.5% IDR
                'Moderate': 0.015,    # 1.5% IDR
                'Extensive': 0.035,   # 3.5% IDR
                'Complete': 0.080,    # 8.0% IDR (collapse)
            },
            'max_analysis_time': 3600,  # 1 hour max per analysis
            'retry_failed': False
        }

    def analyze_building_archetype(self,
                                 building_props: BuildingProperties,
                                 building_id: str = None) -> Optional[FragilityCurveResult]:
        """
        分析單一建築原型

        Args:
            building_props: 建築屬性
            building_id: 建築ID (可選)

        Returns:
            FragilityCurveResult: 易損性曲線結果，失敗時返回None
        """
        start_time = time.time()
        self.analysis_stats['total_requested'] += 1

        archetype_code = building_props.get_archetype_code()

        if building_id is None:
            building_id = archetype_code

        logger.info(f"Starting analysis for archetype: {archetype_code}")

        # 步驟1: 檢查主cache是否已有此archetype的分析結果
        main_cache_result = self._check_main_cache(archetype_code)
        if main_cache_result is not None:
            self.analysis_stats['cache_hits'] += 1
            self.analysis_stats['main_cache_hits'] += 1
            # 直接返回主cache結果，不寫入worker cache以減少檔案數量
            logger.info(f"Using existing result from main cache for {archetype_code}")
            return main_cache_result

        # 步驟2: 檢查當前worker的cache（啟用更新檢查以支援多進程同步）
        cached_result = self.cache_manager.get_fragility_curve(archetype_code, check_updates=True)
        if cached_result is not None:
            self.analysis_stats['cache_hits'] += 1
            self.analysis_stats['worker_cache_hits'] += 1
            logger.info(f"Worker cache hit for {archetype_code}")
            return cached_result

        # 執行新分析
        logger.info(f"Performing new analysis for {archetype_code}")
        self.analysis_stats['new_analyses'] += 1

        # 1. 生成Stick Model參數 - NO ERROR HANDLING
        logger.info(f"Generating model parameters for {archetype_code}...")
        model_params = self.archetype_generator.generate_stick_model_parameters(
            building_props, building_id
        )

        if not model_params.stories:
            logger.error(f"Failed to generate model parameters for {archetype_code}")
            self.analysis_stats['failed_analyses'] += 1
            return None

        # 2. 轉換為舊格式以相容現有系統
        model_properties = []

        # 驗證 model_params.stories 的類型和內容
        if not hasattr(model_params, 'stories'):
            logger.error(f"model_params missing 'stories' attribute for {archetype_code}")
            self.analysis_stats['failed_analyses'] += 1
            return None

        if not isinstance(model_params.stories, list):
            logger.error(f"model_params.stories is not a list for {archetype_code}: {type(model_params.stories)}")
            self.analysis_stats['failed_analyses'] += 1
            return None

        for i, story in enumerate(model_params.stories):
            # 檢查每個 story 對象是否有必要的屬性
            required_attrs = ['story', 'mass', 'k', 'Fy', 'alpha', 'story_height', 'material_type']
            missing_attrs = [attr for attr in required_attrs if not hasattr(story, attr)]

            if missing_attrs:
                logger.error(f"Story {i} missing attributes {missing_attrs} for {archetype_code}")
                logger.error(f"Story object type: {type(story)}")
                logger.error(f"Story object attributes: {dir(story) if hasattr(story, '__dict__') else 'No attributes'}")
                self.analysis_stats['failed_analyses'] += 1
                return None

            # NO ERROR HANDLING for attribute access
            story_data = {
                'story': story.story,
                'mass': story.mass,
                'k': story.k,
                'Fy': story.Fy,
                'alpha': story.alpha,
                'story_height': story.story_height,
                'material_type': story.material_type
            }
            model_properties.append(story_data)

        logger.debug(f"Generated {len(model_properties)} story parameters")

        # 3. 執行IDA分析 - NO ERROR HANDLING
        logger.info(f"Starting IDA analysis for {archetype_code}...")
        ida_results = self._perform_ida_analysis(
            building_id, model_properties
        )

        if ida_results is None or ida_results.empty:
            logger.error(f"IDA analysis failed for {archetype_code}")
            self.analysis_stats['failed_analyses'] += 1
            return None

        # 4. 易損性分析 - NO ERROR HANDLING
        logger.info(f"Starting fragility analysis for {archetype_code}...")
        fragility_analyzer = FragilityAnalyzer(
            ida_results, self.analysis_config['damage_states']
        )

        # 擬合易損性曲線
        fragility_params = fragility_analyzer.fit_all_fragility_curves()

        if not fragility_params:
            logger.error(f"Fragility curve fitting failed for {archetype_code}")
            self.analysis_stats['failed_analyses'] += 1
            return None

        # 5. 生成標準化結果
        analysis_metadata = {
            'building_archetype': archetype_code,
            'structural_system': building_props.structural_system,
            'construction_era': building_props.construction_era,
            'floor_count': building_props.floor_count,
            'area_scale': building_props.area_scale,
            'analysis_config': self.analysis_config
        }

        standard_result = fragility_analyzer.export_standard_fragility_result(
            analysis_metadata=analysis_metadata
        )

        if not standard_result:
            logger.error(f"Failed to export standard result for {archetype_code}")
            self.analysis_stats['failed_analyses'] += 1
            return None

        # 6. 建立快取結果
        computation_time = time.time() - start_time
        standard_result['computation_time'] = computation_time

        cache_result = FragilityCurveResult(
            archetype_code=archetype_code,
            **standard_result
        )

        # 7. 儲存到快取
        self.cache_manager.store_fragility_curve(cache_result)

        # 標記有新結果需要保存
        self.has_new_results = True

        # 更新統計
        self.analysis_stats['total_computation_time'] += computation_time

        logger.info(f"Successfully analyzed {archetype_code} in {computation_time:.1f}s")
        return cache_result

    def _perform_ida_analysis(self, building_id: str, model_properties: List[Dict]) -> Optional[Any]:
        """
        執行IDA分析

        Args:
            building_id: 建築ID
            model_properties: 模型參數

        Returns:
            IDA分析結果DataFrame
        """
        # 建立Stick Model - 打印詳細參數用於調試
        logger.info(f"Creating StickModel for {building_id} with {len(model_properties)} stories")
        for i, props in enumerate(model_properties):
            logger.info(f"  Story {props['story']}: mass={props['mass']:.6f}, k={props['k']:.1e}, "
                       f"Fy={props['Fy']:.1f}, alpha={props['alpha']:.3f}, height={props['story_height']:.1f}")

        stick_model = StickModel(model_properties, damping_ratio=self.analysis_config['damping_ratio'])

        # 建立模型
        logger.info(f"Building OpenSees model for {building_id}...")
        model_success = stick_model.build_model()
        if not model_success:
            logger.error(f"Failed to build OpenSees model for {building_id}")
            return None
        logger.info(f"OpenSees model built successfully for {building_id}")

        # 建立IDA引擎
        ida_engine = IDAEngine(
            stick_model,
            self.gm_processor,
            self.analysis_config
        )

        # 執行IDA分析
        results_df = ida_engine.run_full_ida()

        if results_df is None or results_df.empty:
            logger.warning(f"IDA analysis returned empty results for {building_id}")
            return None

        logger.debug(f"IDA analysis completed: {len(results_df)} results")
        return results_df

        # except Exception as e:
        #     import traceback
        #     logger.error(f"IDA analysis error for {building_id}: {e}")
        #     logger.error(f"Full traceback: {traceback.format_exc()}")
        #     return None

    def batch_analyze(self,
                     building_props_list: List[Tuple[BuildingProperties, str]],
                     max_parallel: int = 1) -> Dict[str, Optional[FragilityCurveResult]]:
        """
        批量分析多個建築原型

        Args:
            building_props_list: 建築屬性和ID的列表
            max_parallel: 最大並行數 (目前僅支援序列處理)

        Returns:
            Dict[str, FragilityCurveResult]: 分析結果字典
        """
        results = {}
        total_count = len(building_props_list)

        logger.info(f"Starting batch analysis of {total_count} buildings")
        start_time = time.time()

        for i, (building_props, building_id) in enumerate(building_props_list):
            archetype_code = building_props.get_archetype_code()

            logger.info(f"Processing {i+1}/{total_count}: {archetype_code}")

            result = self.analyze_building_archetype(building_props, building_id)
            results[building_id] = result

            # 進度報告
            if (i + 1) % 10 == 0 or i == total_count - 1:
                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1)
                remaining = (total_count - i - 1) * avg_time

                logger.info(f"Progress: {i+1}/{total_count} "
                           f"({(i+1)/total_count*100:.1f}%), "
                           f"ETA: {remaining/60:.1f} min")

        # 最終統計
        total_time = time.time() - start_time
        successful = sum(1 for r in results.values() if r is not None)

        logger.info(f"Batch analysis completed in {total_time/60:.1f} minutes")
        logger.info(f"Results: {successful}/{total_count} successful")
        logger.info(f"Cache hits: {self.analysis_stats['cache_hits']} "
                   f"(Main: {self.analysis_stats['main_cache_hits']}, "
                   f"Worker: {self.analysis_stats['worker_cache_hits']})")
        logger.info(f"New analyses: {self.analysis_stats['new_analyses']}")
        logger.info(f"Failed analyses: {self.analysis_stats['failed_analyses']}")

        return results

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        獲取分析統計資訊

        Returns:
            Dict: 統計資訊
        """
        stats = self.analysis_stats.copy()

        # 計算額外統計
        if stats['total_requested'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_requested']
            stats['main_cache_hit_rate'] = stats['main_cache_hits'] / stats['total_requested']
            stats['worker_cache_hit_rate'] = stats['worker_cache_hits'] / stats['total_requested']
            stats['success_rate'] = (stats['total_requested'] - stats['failed_analyses']) / stats['total_requested']
        else:
            stats['cache_hit_rate'] = 0.0
            stats['main_cache_hit_rate'] = 0.0
            stats['worker_cache_hit_rate'] = 0.0
            stats['success_rate'] = 0.0

        if stats['new_analyses'] > 0:
            stats['avg_computation_time'] = stats['total_computation_time'] / stats['new_analyses']
        else:
            stats['avg_computation_time'] = 0.0

        # 加入快取統計
        cache_stats = self.cache_manager.get_cache_statistics()
        stats['cache_stats'] = {
            'total_entries': cache_stats.total_entries,
            'cache_file_size_mb': cache_stats.cache_file_size_mb,
            'overall_hit_rate': cache_stats.hit_rate
        }

        return stats

    def save_final_cache(self) -> None:
        """儲存最終快取檔案（僅當有新計算結果時）"""
        if not self.has_new_results:
            logger.info("No new results to save, skipping cache save")
            return

        try:
            self.cache_manager.save_cache()
            logger.info("Final cache saved successfully with new results")
        except Exception as e:
            logger.error(f"Failed to save final cache: {e}")

    def cleanup_old_cache_entries(self, max_age_days: int = 30) -> int:
        """清理過期的快取項目"""
        try:
            removed = self.cache_manager.cleanup_old_entries(max_age_days)
            logger.info(f"Cleaned up {removed} old cache entries")
            return removed
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return 0


def test_batch_analyzer():
    """測試批量分析器"""
    from building_classifier import BuildingProperties

    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    print("Testing Batch Fragility Analyzer...")

    # 建立測試資料
    test_buildings = [
        BuildingProperties(
            floor_count=5,
            structural_system='RC',
            construction_era='PRE',
            area_scale='S',
            area_sqm=120.0,
            height=17.5,
            age=30
        ),
        BuildingProperties(
            floor_count=8,
            structural_system='RC',
            construction_era='POST',
            area_scale='M',
            area_sqm=300.0,
            height=28.0,
            age=15
        )
    ]

    # 準備分析列表
    building_list = [
        (building, building.get_archetype_code())
        for building in test_buildings
    ]

    # 注意：這個測試需要實際的地震波檔案才能執行
    # 這裡只是展示用法
    print(f"Would analyze {len(building_list)} buildings:")
    for building, building_id in building_list:
        print(f"  - {building_id}")

    print("Note: Actual analysis requires ground motion files")


if __name__ == "__main__":
    test_batch_analyzer()