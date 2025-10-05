#!/usr/bin/env python3
"""
Progress Tracking and Logging Module

此模組提供詳細的進度追蹤和日誌功能，支援大規模分析任務的監控。

主要功能：
1. 實時進度追蹤
2. 詳細日誌記錄
3. 效能監控
4. 錯誤統計
5. 結果報告生成
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class TaskMetrics:
    """任務指標"""
    task_id: str
    archetype_code: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    cache_hit: bool = False
    computation_time: float = 0.0


class PerformanceMonitor:
    """效能監控器"""

    def __init__(self, window_size: int = 100):
        """
        初始化效能監控器

        Args:
            window_size: 滑動窗口大小，用於計算近期統計
        """
        self.window_size = window_size
        self.task_metrics: List[TaskMetrics] = []
        self.lock = threading.Lock()

    def record_task(self, metrics: TaskMetrics) -> None:
        """記錄任務指標"""
        with self.lock:
            self.task_metrics.append(metrics)

            # 保持滑動窗口大小
            if len(self.task_metrics) > self.window_size * 2:
                self.task_metrics = self.task_metrics[-self.window_size:]

    def get_recent_performance(self) -> Dict[str, Any]:
        """獲取近期效能統計"""
        with self.lock:
            if not self.task_metrics:
                return {}

            # 取最近的任務
            recent_tasks = self.task_metrics[-min(self.window_size, len(self.task_metrics)):]

            completed_tasks = [t for t in recent_tasks if t.end_time is not None]

            if not completed_tasks:
                return {}

            # 計算統計
            computation_times = [t.computation_time for t in completed_tasks if t.computation_time > 0]
            success_count = sum(1 for t in completed_tasks if t.success)
            cache_hit_count = sum(1 for t in completed_tasks if t.cache_hit)

            stats = {
                'total_tasks': len(completed_tasks),
                'successful_tasks': success_count,
                'failed_tasks': len(completed_tasks) - success_count,
                'cache_hits': cache_hit_count,
                'success_rate': success_count / len(completed_tasks) if completed_tasks else 0,
                'cache_hit_rate': cache_hit_count / len(completed_tasks) if completed_tasks else 0,
            }

            if computation_times:
                stats.update({
                    'avg_computation_time': sum(computation_times) / len(computation_times),
                    'min_computation_time': min(computation_times),
                    'max_computation_time': max(computation_times),
                    'total_computation_time': sum(computation_times)
                })

            return stats


class DetailedProgressTracker:
    """詳細進度追蹤器"""

    def __init__(self,
                 total_tasks: int,
                 report_interval: float = 30.0,
                 log_file: Optional[str] = None):
        """
        初始化進度追蹤器

        Args:
            total_tasks: 總任務數
            report_interval: 報告間隔（秒）
            log_file: 日誌檔案路徑
        """
        self.total_tasks = total_tasks
        self.report_interval = report_interval
        self.log_file = Path(log_file) if log_file else None

        # 統計資料
        self.completed_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.cache_hits = 0
        self.new_analyses = 0

        # 時間追蹤
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.last_checkpoint_time = time.time()

        # 效能監控
        self.performance_monitor = PerformanceMonitor()

        # 錯誤記錄
        self.error_log: List[Dict[str, Any]] = []

        # 階段性統計
        self.checkpoints: List[Dict[str, Any]] = []

        # 回調函數
        self.progress_callbacks: List[Callable[[Dict], None]] = []

        # 執行緒安全
        self.lock = threading.Lock()

        logger.info(f"Progress tracker initialized for {total_tasks} tasks")

    def add_progress_callback(self, callback: Callable[[Dict], None]) -> None:
        """添加進度回調函數"""
        self.progress_callbacks.append(callback)

    def update_task_completion(self,
                             task_id: str,
                             archetype_code: str,
                             success: bool,
                             computation_time: float = 0.0,
                             cache_hit: bool = False,
                             error_message: Optional[str] = None) -> None:
        """
        更新任務完成狀態

        Args:
            task_id: 任務ID
            archetype_code: 建築原型編碼
            success: 是否成功
            computation_time: 計算時間
            cache_hit: 是否為快取命中
            error_message: 錯誤訊息
        """
        with self.lock:
            self.completed_tasks += 1

            # 記錄任務指標
            metrics = TaskMetrics(
                task_id=task_id,
                archetype_code=archetype_code,
                start_time=time.time() - computation_time,
                end_time=time.time(),
                success=success,
                error_message=error_message,
                cache_hit=cache_hit,
                computation_time=computation_time
            )

            self.performance_monitor.record_task(metrics)

            # 更新統計
            if success:
                self.successful_tasks += 1
                if cache_hit:
                    self.cache_hits += 1
                else:
                    self.new_analyses += 1
            else:
                self.failed_tasks += 1

                # 記錄錯誤
                self.error_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'task_id': task_id,
                    'archetype_code': archetype_code,
                    'error_message': error_message
                })

            # 檢查是否需要報告進度
            if self.should_report_progress():
                self.report_progress()

    def should_report_progress(self) -> bool:
        """檢查是否需要報告進度"""
        current_time = time.time()
        return (current_time - self.last_report_time) >= self.report_interval

    def report_progress(self) -> None:
        """報告當前進度"""
        with self.lock:
            current_time = time.time()
            self.last_report_time = current_time

            progress_data = self.get_current_progress()

            # 記錄到日誌
            logger.info(f"Progress Report:\n{self.format_progress_report(progress_data)}")

            # 觸發回調
            for callback in self.progress_callbacks:
                try:
                    callback(progress_data)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

            # 寫入檔案（如果指定）
            if self.log_file:
                self.write_progress_to_file(progress_data)

    def get_current_progress(self) -> Dict[str, Any]:
        """獲取當前進度資料"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        progress_pct = (self.completed_tasks / self.total_tasks * 100) if self.total_tasks > 0 else 0

        # 計算剩餘時間
        if self.completed_tasks > 0:
            avg_task_time = elapsed_time / self.completed_tasks
            remaining_tasks = self.total_tasks - self.completed_tasks
            eta_seconds = remaining_tasks * avg_task_time
        else:
            eta_seconds = 0

        # 獲取近期效能
        recent_performance = self.performance_monitor.get_recent_performance()

        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'successful_tasks': self.successful_tasks,
            'failed_tasks': self.failed_tasks,
            'cache_hits': self.cache_hits,
            'new_analyses': self.new_analyses,
            'progress_percentage': progress_pct,
            'elapsed_time_seconds': elapsed_time,
            'estimated_remaining_seconds': eta_seconds,
            'recent_performance': recent_performance
        }

        return progress_data

    def format_progress_report(self, progress_data: Dict[str, Any]) -> str:
        """格式化進度報告"""
        elapsed_min = progress_data['elapsed_time_seconds'] / 60
        eta_min = progress_data['estimated_remaining_seconds'] / 60

        report = f"Progress: {progress_data['completed_tasks']}/{progress_data['total_tasks']} "
        report += f"({progress_data['progress_percentage']:.1f}%)\n"
        report += f"  Successful: {progress_data['successful_tasks']}\n"
        report += f"  Failed: {progress_data['failed_tasks']}\n"
        report += f"  Cache hits: {progress_data['cache_hits']}\n"
        report += f"  New analyses: {progress_data['new_analyses']}\n"
        report += f"  Elapsed: {elapsed_min:.1f} min\n"
        report += f"  ETA: {eta_min:.1f} min"

        # 添加近期效能資訊
        recent_perf = progress_data.get('recent_performance', {})
        if recent_perf:
            report += f"\n  Recent success rate: {recent_perf.get('success_rate', 0):.1%}"
            if 'avg_computation_time' in recent_perf:
                report += f"\n  Avg task time: {recent_perf['avg_computation_time']:.1f}s"

        return report

    def write_progress_to_file(self, progress_data: Dict[str, Any]) -> None:
        """寫入進度到檔案"""
        try:
            if not self.log_file:
                return

            # 確保目錄存在
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            # 讀取現有資料
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'progress_history': [], 'error_log': []}

            # 添加當前進度
            data['progress_history'].append(progress_data)

            # 更新錯誤日誌
            data['error_log'] = self.error_log

            # 寫回檔案
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to write progress to file: {e}")

    def create_checkpoint(self, checkpoint_name: str) -> None:
        """建立檢查點"""
        with self.lock:
            checkpoint_data = self.get_current_progress()
            checkpoint_data['checkpoint_name'] = checkpoint_name

            self.checkpoints.append(checkpoint_data)
            self.last_checkpoint_time = time.time()

            logger.info(f"Checkpoint '{checkpoint_name}' created at {self.completed_tasks}/{self.total_tasks}")

    def get_final_summary(self) -> Dict[str, Any]:
        """獲取最終總結"""
        final_progress = self.get_current_progress()
        total_time = time.time() - self.start_time

        summary = {
            **final_progress,
            'total_processing_time_seconds': total_time,
            'average_task_time_seconds': total_time / self.completed_tasks if self.completed_tasks > 0 else 0,
            'throughput_tasks_per_minute': self.completed_tasks / (total_time / 60) if total_time > 0 else 0,
            'error_log': self.error_log,
            'checkpoints': self.checkpoints,
            'overall_success_rate': self.successful_tasks / self.completed_tasks if self.completed_tasks > 0 else 0,
            'overall_cache_hit_rate': self.cache_hits / self.completed_tasks if self.completed_tasks > 0 else 0
        }

        return summary

    def save_final_report(self, output_file: str) -> None:
        """儲存最終報告"""
        try:
            summary = self.get_final_summary()

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info(f"Final report saved to: {output_file}")

        except Exception as e:
            logger.error(f"Failed to save final report: {e}")

    def print_final_summary(self) -> None:
        """列印最終總結"""
        summary = self.get_final_summary()

        print("\n" + "="*60)
        print("FINAL PROCESSING SUMMARY")
        print("="*60)

        print(f"Total tasks: {summary['total_tasks']}")
        print(f"Completed: {summary['completed_tasks']}")
        print(f"Successful: {summary['successful_tasks']}")
        print(f"Failed: {summary['failed_tasks']}")
        print(f"Cache hits: {summary['cache_hits']}")
        print(f"New analyses: {summary['new_analyses']}")

        print(f"\nRates:")
        print(f"Success rate: {summary['overall_success_rate']:.1%}")
        print(f"Cache hit rate: {summary['overall_cache_hit_rate']:.1%}")

        print(f"\nTiming:")
        print(f"Total time: {summary['total_processing_time_seconds']/3600:.1f} hours")
        print(f"Average task time: {summary['average_task_time_seconds']:.1f} seconds")
        print(f"Throughput: {summary['throughput_tasks_per_minute']:.1f} tasks/minute")

        if summary['error_log']:
            print(f"\nErrors: {len(summary['error_log'])} errors occurred")
            print("Recent errors:")
            for error in summary['error_log'][-5:]:
                print(f"  - {error['archetype_code']}: {error['error_message'][:100]}")

        print("="*60)


def setup_comprehensive_logging(log_dir: str = "logs",
                               log_level: str = "INFO",
                               max_log_files: int = 10) -> None:
    """
    設定全面的日誌系統

    Args:
        log_dir: 日誌目錄
        log_level: 日誌級別
        max_log_files: 最大日誌檔案數
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 建立時間戳檔名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"fragility_analysis_{timestamp}.log"

    # 設定根日誌記錄器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 清除現有處理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 檔案處理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 清理舊日誌檔案
    log_files = sorted(log_path.glob("fragility_analysis_*.log"))
    if len(log_files) > max_log_files:
        for old_log in log_files[:-max_log_files]:
            try:
                old_log.unlink()
                logger.debug(f"Removed old log file: {old_log}")
            except Exception as e:
                logger.warning(f"Failed to remove old log file {old_log}: {e}")

    logger.info(f"Comprehensive logging setup complete")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {log_level}")


def test_progress_tracker():
    """測試進度追蹤器"""
    import tempfile
    import random

    print("Testing Detailed Progress Tracker...")

    # 建立臨時日誌檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_log_file = f.name

    try:
        # 初始化追蹤器
        tracker = DetailedProgressTracker(
            total_tasks=20,
            report_interval=2.0,  # 2秒報告間隔
            log_file=temp_log_file
        )

        # 模擬任務執行
        for i in range(20):
            task_id = f"task_{i:03d}"
            archetype_code = f"RC-PRE-{5+i%10}F-S"

            # 模擬不同的結果
            success = random.random() > 0.1  # 90%成功率
            cache_hit = random.random() < 0.3  # 30%快取命中率
            computation_time = random.uniform(0.5, 5.0) if not cache_hit else random.uniform(0.01, 0.1)

            error_message = None if success else f"Simulated error for {task_id}"

            tracker.update_task_completion(
                task_id=task_id,
                archetype_code=archetype_code,
                success=success,
                computation_time=computation_time,
                cache_hit=cache_hit,
                error_message=error_message
            )

            # 在中間建立檢查點
            if i == 9:
                tracker.create_checkpoint("Halfway Point")

            # 短暫延遲
            time.sleep(0.1)

        # 最終總結
        tracker.print_final_summary()

        # 儲存最終報告
        tracker.save_final_report("test_final_report.json")

        print(f"Test completed. Log file: {temp_log_file}")

    finally:
        # 清理
        if os.path.exists(temp_log_file):
            os.unlink(temp_log_file)


if __name__ == "__main__":
    # 設定日誌
    setup_comprehensive_logging(log_level="DEBUG")

    # 執行測試
    test_progress_tracker()