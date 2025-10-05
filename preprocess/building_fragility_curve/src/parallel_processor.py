#!/usr/bin/env python3
"""
Parallel Fragility Processing Module

此模組提供多程序平行處理功能，用於大規模建築易損性分析。
支援進程池管理、任務分配、結果收集和錯誤處理。

主要功能：
1. 多程序任務分發
2. 進程池管理
3. 動態負載平衡
4. 結果收集和合併
5. 錯誤恢復和重試
"""

import os
import sys
import time
import logging
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Callable
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import signal
import traceback
import pickle

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from building_classifier import BuildingProperties
from fragility_cache import FragilityCurveResult

logger = logging.getLogger(__name__)


class WorkerConfig:
    """工作程序配置"""
    def __init__(self,
                 gm_directory: str,
                 gm_list_file: str,
                 cache_file: str,
                 analysis_config: Dict,
                 worker_id: Optional[str] = None):
        self.gm_directory = gm_directory
        self.gm_list_file = gm_list_file
        self.cache_file = cache_file
        self.analysis_config = analysis_config
        self.worker_id = worker_id


class TaskResult:
    """任務結果封裝"""
    def __init__(self,
                 building_id: str,
                 archetype_code: str,
                 success: bool,
                 result: Optional[FragilityCurveResult] = None,
                 error: Optional[str] = None,
                 computation_time: float = 0.0):
        self.building_id = building_id
        self.archetype_code = archetype_code
        self.success = success
        self.result = result
        self.error = error
        self.computation_time = computation_time


class ProgressTracker:
    """進度追蹤器"""
    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.cache_hits = 0
        self.new_analyses = 0
        self.start_time = time.time()
        self.last_report_time = time.time()

    def update(self, task_result: TaskResult):
        """更新進度"""
        self.completed_tasks += 1

        if task_result.success:
            # 檢查是否為快取命中（計算時間很短）
            if task_result.computation_time < 1.0:
                self.cache_hits += 1
            else:
                self.new_analyses += 1
        else:
            self.failed_tasks += 1

    def should_report(self, report_interval: float = 30.0) -> bool:
        """判斷是否應該報告進度"""
        current_time = time.time()
        return (current_time - self.last_report_time) >= report_interval

    def get_progress_report(self) -> str:
        """獲取進度報告"""
        elapsed = time.time() - self.start_time
        progress_pct = (self.completed_tasks / self.total_tasks) * 100 if self.total_tasks > 0 else 0

        # 估算剩餘時間
        if self.completed_tasks > 0:
            avg_time = elapsed / self.completed_tasks
            remaining_tasks = self.total_tasks - self.completed_tasks
            eta_seconds = remaining_tasks * avg_time
            eta_minutes = eta_seconds / 60
        else:
            eta_minutes = 0

        report = f"Progress: {self.completed_tasks}/{self.total_tasks} ({progress_pct:.1f}%)\n"
        report += f"  Success: {self.completed_tasks - self.failed_tasks}, Failed: {self.failed_tasks}\n"
        report += f"  Cache hits: {self.cache_hits}, New analyses: {self.new_analyses}\n"
        report += f"  Elapsed: {elapsed/60:.1f} min, ETA: {eta_minutes:.1f} min"

        self.last_report_time = time.time()
        return report


def worker_analyze_building(task_data: Tuple[BuildingProperties, str, WorkerConfig]) -> TaskResult:
    """
    工作程序函數：分析單一建築
    WARNING: ALL ERROR HANDLING REMOVED FOR DEBUGGING - WILL CRASH ON ANY ERROR

    Args:
        task_data: (building_props, building_id, worker_config) 的元組

    Returns:
        TaskResult: 任務結果
    """
    building_props, building_id, config = task_data

    # 型別檢查：確保 building_props 是 BuildingProperties 物件
    if not isinstance(building_props, BuildingProperties):
        error_msg = (f"Type error: building_props should be BuildingProperties object, "
                    f"but got {type(building_props).__name__}: {building_props}")
        logger.error(error_msg)
        raise TypeError(error_msg)

    # 確保 building_id 是字串
    if not isinstance(building_id, str):
        building_id = str(building_id)
        logger.warning(f"building_id converted to string: {building_id}")

    # Get archetype code - NO ERROR HANDLING
    archetype_code = building_props.get_archetype_code()

    start_time = time.time()

    # 在每個工作程序中初始化分析器
    # 注意：由於多程序的限制，我們需要在工作程序中重新建立對象
    from batch_fragility_analyzer import BatchFragilityAnalyzer

    analyzer = BatchFragilityAnalyzer(
        gm_directory=config.gm_directory,
        gm_list_file=config.gm_list_file,
        cache_file=config.cache_file,
        analysis_config=config.analysis_config,
        worker_id=config.worker_id
    )

    # 執行分析 - NO ERROR HANDLING
    logger.info(f"Starting analysis for {building_id} ({archetype_code})")
    logger.info(f"Building properties: area={building_props.area_sqm:.2f}m², "
               f"floors={building_props.floor_count}, system={building_props.structural_system}, "
               f"era={building_props.construction_era}")
    result = analyzer.analyze_building_archetype(building_props, building_id)
    computation_time = time.time() - start_time

    # 確保 cache 被保存（每個 worker 都要保存自己的結果）
    try:
        analyzer.save_final_cache()
        logger.debug(f"Cache saved successfully for worker processing {building_id}")
    except Exception as e:
        logger.warning(f"Failed to save cache for {building_id}: {e}")

    if result is not None:
        logger.info(f"Analysis successful for {building_id} in {computation_time:.1f}s")
        return TaskResult(
            building_id=building_id,
            archetype_code=archetype_code,
            success=True,
            result=result,
            computation_time=computation_time
        )
    else:
        logger.error(f"Analysis returned None for {building_id}")
        return TaskResult(
            building_id=building_id,
            archetype_code=archetype_code,
            success=False,
            error="Analysis returned None",
            computation_time=computation_time
        )


class ParallelFragilityProcessor:
    """
    平行易損性處理器

    管理多程序分析任務，提供高效的大規模建築分析能力
    """

    def __init__(self,
                 max_workers: int = None,
                 gm_directory: str = None,
                 gm_list_file: str = None,
                 cache_file: str = "fragility_cache.json",
                 analysis_config: Dict = None):
        """
        初始化平行處理器

        Args:
            max_workers: 最大工作程序數，預設為CPU核心數-1
            gm_directory: 地震波檔案目錄
            gm_list_file: 地震波清單檔案
            cache_file: 快取檔案路徑
            analysis_config: 分析配置
        """
        # 設定工作程序數量
        cpu_count = mp.cpu_count()
        if max_workers is None:
            # 保留一個核心給系統使用
            self.max_workers = max(1, cpu_count - 1)
        else:
            self.max_workers = min(max_workers, cpu_count)

        # 工作程序配置
        self.worker_config = WorkerConfig(
            gm_directory=gm_directory,
            gm_list_file=gm_list_file,
            cache_file=cache_file,
            analysis_config=analysis_config or {}
        )

        # 主cache管理器（僅用於合併操作）
        from fragility_cache import FragilityCacheManager
        self.main_cache_manager = FragilityCacheManager(cache_file, worker_id=None)

        # 統計資訊
        self.stats = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'cache_hits': 0,
            'new_analyses': 0,
            'total_computation_time': 0.0,
            'parallel_processing_time': 0.0,
            'average_task_time': 0.0
        }

        logger.info(f"Parallel processor initialized with {self.max_workers} workers")
        logger.info(f"CPU cores available: {cpu_count}")

    def process_buildings_parallel(self,
                                 building_tasks: List[Tuple[BuildingProperties, str]],
                                 progress_callback: Optional[Callable[[str], None]] = None,
                                 report_interval: float = 30.0) -> Dict[str, Optional[FragilityCurveResult]]:
        """
        平行處理多個建築分析任務

        Args:
            building_tasks: 建築任務列表 [(building_props, building_id), ...]
            progress_callback: 進度回調函數
            report_interval: 進度報告間隔（秒）

        Returns:
            Dict[str, FragilityCurveResult]: 分析結果字典
        """
        # 預先驗證任務資料
        valid_tasks = []
        invalid_count = 0

        logger.info(f"Validating {len(building_tasks)} building tasks...")

        for i, task in enumerate(building_tasks):
            try:
                if not isinstance(task, tuple) or len(task) != 2:
                    logger.error(f"Task {i}: Invalid task format - expected tuple of length 2, got {type(task)}")
                    invalid_count += 1
                    continue

                building_props, building_id = task

                # 驗證 BuildingProperties 物件
                if not isinstance(building_props, BuildingProperties):
                    logger.error(f"Task {i} (building_id: {building_id}): Expected BuildingProperties, got {type(building_props)}")
                    invalid_count += 1
                    continue

                # 驗證物件有效性
                if hasattr(building_props, 'validate') and not building_props.validate():
                    logger.error(f"Task {i} (building_id: {building_id}): BuildingProperties validation failed")
                    invalid_count += 1
                    continue

                # 驗證 building_id
                if not isinstance(building_id, str) or not building_id.strip():
                    logger.warning(f"Task {i}: Invalid building_id {building_id}, converting to string")
                    building_id = str(building_id) if building_id else f"building_{i:06d}"

                valid_tasks.append((building_props, building_id))

            except Exception as e:
                logger.error(f"Task {i}: Validation error - {e}")
                invalid_count += 1

        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} invalid tasks")

        total_tasks = len(valid_tasks)
        if total_tasks == 0:
            logger.warning("No valid buildings to process after validation")
            return {}

        logger.info(f"Starting parallel processing of {total_tasks} valid buildings")
        logger.info(f"Using {self.max_workers} worker processes")

        # 初始化統計和追蹤
        self.stats['total_tasks'] = total_tasks
        progress_tracker = ProgressTracker(total_tasks)
        results = {}

        # 準備工作任務（使用驗證過的資料）
        # 為每個任務創建帶有唯一worker_id的config
        worker_tasks = []
        for i, (building_props, building_id) in enumerate(valid_tasks):
            # 創建帶有唯一worker_id的config副本
            worker_config = WorkerConfig(
                gm_directory=self.worker_config.gm_directory,
                gm_list_file=self.worker_config.gm_list_file,
                cache_file=self.worker_config.cache_file,
                analysis_config=self.worker_config.analysis_config,
                worker_id=f"w{i:04d}"  # 格式化為 w0001, w0002, etc.
            )
            worker_tasks.append((building_props, building_id, worker_config))

        parallel_start_time = time.time()

        # 在提交任務前進行建築參數預驗證 - NO ERROR HANDLING
        validated_tasks = []
        for task in worker_tasks:
            if self._validate_building_parameters(task[0], task[1]):  # building_props, building_id
                validated_tasks.append(task)
            else:
                logger.error(f"Building parameter validation failed for {task[1]}, skipping")
                self.stats['failed_tasks'] += 1

        if not validated_tasks:
            logger.error("No valid building tasks to process")
            return {}

        logger.info(f"Pre-validation completed: {len(validated_tasks)}/{len(worker_tasks)} tasks valid")

        # 使用ProcessPoolExecutor進行平行處理 - NO ERROR HANDLING
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有已驗證的任務
            future_to_task = {
                executor.submit(worker_analyze_building, task): task
                for task in validated_tasks
            }

            logger.info(f"Submitted {len(future_to_task)} tasks to worker pool")

            # 收集結果 - NO ERROR HANDLING, WILL CRASH ON ANY WORKER ERROR
            logger.info("Starting to collect results from workers...")
            completed_count = 0

            for future in as_completed(future_to_task):
                # Get task result - NO ERROR HANDLING
                task_result = future.result()
                building_id = task_result.building_id

                # 更新進度追蹤
                progress_tracker.update(task_result)
                completed_count += 1

                # 儲存結果
                if task_result.success:
                    results[building_id] = task_result.result
                    self.stats['successful_tasks'] += 1
                    logger.info(f"SUCCESS: {building_id} completed in {task_result.computation_time:.1f}s")

                    # 更新計算時間統計
                    self.stats['total_computation_time'] += task_result.computation_time

                    # 區分快取命中和新分析
                    if task_result.computation_time < 1.0:
                        self.stats['cache_hits'] += 1
                    else:
                        self.stats['new_analyses'] += 1

                else:
                    results[building_id] = None
                    self.stats['failed_tasks'] += 1
                    logger.error(f"FAILED: {building_id} - {task_result.error}")

                # 每3個任務合併一次cache
                if completed_count % 3 == 0:
                    try:
                        merge_stats = self.main_cache_manager.merge_worker_caches()
                        logger.info(f"Cache merge (every 3 tasks): {merge_stats['new_entries_added']} new entries, "
                                  f"{merge_stats['entries_updated']} updated entries")

                        # 保存合併後的主cache
                        self.main_cache_manager.save_cache()

                    except Exception as e:
                        logger.warning(f"Failed to merge worker caches: {e}")

                # 進度報告
                # if progress_tracker.should_report(report_interval):
                #     progress_report = progress_tracker.get_progress_report()
                #     logger.info(f"Progress Update:\n{progress_report}")

                #     if progress_callback:
                #         progress_callback(progress_report)

        # 最終統計
        parallel_time = time.time() - parallel_start_time
        self.stats['parallel_processing_time'] = parallel_time

        if self.stats['successful_tasks'] > 0:
            self.stats['average_task_time'] = (
                self.stats['total_computation_time'] / self.stats['successful_tasks']
            )

        # 最終cache合併和清理
        try:
            logger.info("Performing final cache merge and cleanup...")
            final_merge_stats = self.main_cache_manager.merge_worker_caches()
            logger.info(f"Final cache merge: {final_merge_stats}")

            # 保存最終的主cache
            self.main_cache_manager.save_cache()

            # 清理worker cache檔案
            cleaned_files = self.main_cache_manager.cleanup_worker_cache_files()
            logger.info(f"Cleaned up {cleaned_files} worker cache files")

        except Exception as e:
            logger.error(f"Failed to perform final cache operations: {e}")

        # 最終報告
        final_report = self._generate_final_report()
        logger.info(f"Parallel Processing Complete:\n{final_report}")

        if progress_callback:
            progress_callback(final_report)

        return results

    def _validate_building_parameters(self, building_props: BuildingProperties, building_id: str) -> bool:
        """
        驗證建築參數是否適合進行易損性分析

        Args:
            building_props: 建築屬性
            building_id: 建築ID

        Returns:
            bool: True if parameters are valid
        """
        try:
            # 檢查必要屬性是否存在
            required_attrs = ['area_sqm', 'floor_count', 'structural_system']
            for attr in required_attrs:
                if not hasattr(building_props, attr):
                    logger.error(f"Missing required attribute '{attr}' for building {building_id}")
                    return False

            # 檢查數值範圍
            if building_props.area_sqm <= 0:
                logger.error(f"Invalid area {building_props.area_sqm} for building {building_id}")
                return False

            if building_props.floor_count <= 0 or building_props.floor_count > 50:
                logger.error(f"Invalid floor count {building_props.floor_count} for building {building_id}")
                return False

            if building_props.structural_system not in ['RC', 'SC']:
                logger.error(f"Unknown structural system '{building_props.structural_system}' for building {building_id}")
                return False

            # 檢查是否有可能導致質量問題的極端值
            if building_props.area_sqm < 10:  # 面積過小
                logger.warning(f"Very small area {building_props.area_sqm}m² for building {building_id}, may cause mass issues")

            if building_props.area_sqm > 10000:  # 面積過大
                logger.warning(f"Very large area {building_props.area_sqm}m² for building {building_id}, check parameters")

            logger.debug(f"Building parameter validation passed for {building_id}")
            return True

        except Exception as e:
            logger.error(f"Building parameter validation error for {building_id}: {e}")
            return False

    def _log_problematic_building(self, building_props: BuildingProperties, building_id: str, error_type: str):
        """
        記錄有問題的建築，以便後續分析

        Args:
            building_props: 建築屬性
            building_id: 建築ID
            error_type: 錯誤類型
        """
        try:
            problem_info = {
                'building_id': building_id,
                'error_type': error_type,
                'area_sqm': getattr(building_props, 'area_sqm', 'N/A'),
                'floor_count': getattr(building_props, 'floor_count', 'N/A'),
                'structural_system': getattr(building_props, 'structural_system', 'N/A'),
                'construction_era': getattr(building_props, 'construction_era', 'N/A'),
                'timestamp': datetime.now().isoformat()
            }

            logger.warning(f"Problematic building logged: {problem_info}")

            # 如果需要，可以保存到文件以便後續分析
            # self._save_problematic_building_record(problem_info)

        except Exception as e:
            logger.error(f"Failed to log problematic building {building_id}: {e}")

    def _generate_final_report(self) -> str:
        """生成最終處理報告"""
        stats = self.stats

        report = "=== Parallel Processing Summary ===\n"
        report += f"Total tasks: {stats['total_tasks']}\n"
        report += f"Successful: {stats['successful_tasks']}\n"
        report += f"Failed: {stats['failed_tasks']}\n"
        report += f"Cache hits: {stats['cache_hits']}\n"
        report += f"New analyses: {stats['new_analyses']}\n"
        report += f"Success rate: {stats['successful_tasks']/stats['total_tasks']*100:.1f}%\n"
        report += f"Cache hit rate: {stats['cache_hits']/stats['total_tasks']*100:.1f}%\n"
        report += f"Total processing time: {stats['parallel_processing_time']/60:.1f} minutes\n"

        if stats['new_analyses'] > 0:
            report += f"Average analysis time: {stats['average_task_time']:.1f} seconds\n"

        # 效率分析
        if stats['total_computation_time'] > 0:
            efficiency = stats['parallel_processing_time'] / stats['total_computation_time'] * self.max_workers
            report += f"Parallel efficiency: {efficiency*100:.1f}% (theoretical max: {self.max_workers*100:.0f}%)\n"

        # 錯誤類型分析
        if stats.get('dggev_errors', 0) > 0:
            report += f"DGGEV errors: {stats['dggev_errors']}\n"
        if stats.get('worker_crashes', 0) > 0:
            report += f"Worker crashes: {stats['worker_crashes']}\n"

        return report

    def process_buildings_sequential(self,
                                   building_tasks: List[Tuple[BuildingProperties, str]],
                                   progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Optional[FragilityCurveResult]]:
        """
        序列處理建築分析任務（用於調試或小規模任務）

        Args:
            building_tasks: 建築任務列表
            progress_callback: 進度回調函數

        Returns:
            Dict[str, FragilityCurveResult]: 分析結果字典
        """
        logger.info(f"Starting sequential processing of {len(building_tasks)} buildings")

        from batch_fragility_analyzer import BatchFragilityAnalyzer

        # 建立分析器
        analyzer = BatchFragilityAnalyzer(
            gm_directory=self.worker_config.gm_directory,
            gm_list_file=self.worker_config.gm_list_file,
            cache_file=self.worker_config.cache_file,
            analysis_config=self.worker_config.analysis_config
        )

        # 執行序列分析
        results = analyzer.batch_analyze(building_tasks, max_parallel=1)

        # 更新統計
        self.stats = analyzer.get_analysis_statistics()

        if progress_callback:
            report = self._generate_final_report()
            progress_callback(report)

        return results

    def get_processing_statistics(self) -> Dict[str, Any]:
        """獲取處理統計資訊"""
        return self.stats.copy()

    @staticmethod
    def estimate_processing_time(num_buildings: int,
                               avg_analysis_time: float = 300.0,  # 5 minutes
                               cache_hit_rate: float = 0.5,
                               num_workers: int = None) -> Dict[str, float]:
        """
        估算處理時間

        Args:
            num_buildings: 建築數量
            avg_analysis_time: 平均分析時間（秒）
            cache_hit_rate: 快取命中率
            num_workers: 工作程序數

        Returns:
            Dict: 時間估算結果
        """
        if num_workers is None:
            num_workers = max(1, mp.cpu_count() - 1)

        # 需要進行新分析的建築數量
        new_analyses = int(num_buildings * (1 - cache_hit_rate))
        cache_hits = num_buildings - new_analyses

        # 序列處理時間
        sequential_time = new_analyses * avg_analysis_time + cache_hits * 0.1

        # 平行處理時間（考慮負載均衡和開銷）
        parallel_efficiency = 0.8  # 假設80%的平行效率
        parallel_time = sequential_time / (num_workers * parallel_efficiency)

        # 加上系統開銷
        overhead = max(30, num_buildings * 0.1)  # 最少30秒，每個建築0.1秒開銷
        parallel_time += overhead

        return {
            'num_buildings': num_buildings,
            'new_analyses': new_analyses,
            'cache_hits': cache_hits,
            'sequential_time_minutes': sequential_time / 60,
            'parallel_time_minutes': parallel_time / 60,
            'speedup_factor': sequential_time / parallel_time if parallel_time > 0 else 1,
            'num_workers': num_workers
        }


def test_parallel_processor():
    """測試平行處理器"""
    from building_classifier import BuildingProperties

    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    print("Testing Parallel Fragility Processor...")

    # 建立測試資料
    test_buildings = []
    for i in range(5):  # 小規模測試
        building = BuildingProperties(
            floor_count=5 + i,
            structural_system='RC' if i % 2 == 0 else 'SC',
            construction_era='PRE' if i < 3 else 'POST',
            area_scale='S' if i < 2 else 'M',
            area_sqm=100.0 + i * 50,
            height=17.5 + i * 3,
            age=20 + i * 5
        )
        test_buildings.append(building)

    # 準備任務列表
    building_tasks = [
        (building, f"test_building_{i:03d}")
        for i, building in enumerate(test_buildings)
    ]

    print(f"Created {len(building_tasks)} test buildings")

    # 時間估算
    estimates = ParallelFragilityProcessor.estimate_processing_time(
        len(building_tasks), avg_analysis_time=60.0, cache_hit_rate=0.0
    )

    print("Time estimates:")
    for key, value in estimates.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    print("Note: Actual processing requires ground motion files and analysis setup")


if __name__ == "__main__":
    test_parallel_processor()