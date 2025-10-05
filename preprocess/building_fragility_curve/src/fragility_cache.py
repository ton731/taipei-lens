#!/usr/bin/env python3
"""
Fragility Cache Manager Module

此模組負責管理易損性曲線的快取系統，避免重複計算相同的建築原型。

功能包括：
1. 易損性曲線結果的儲存和讀取
2. 基於原型編碼的索引管理
3. 快取檔案的版本控制和備份
4. 快取統計和效能監控
"""

import json
import os
import logging
import hashlib
import time
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import threading
import fcntl

logger = logging.getLogger(__name__)

@dataclass
class FragilityCurveResult:
    """易損性曲線計算結果"""
    archetype_code: str
    # 震度級別對應的倒塌機率 (3級到7級)
    collapse_probabilities: Dict[str, float]  # {'3': 0.01, '4': 0.03, ...}
    # 分析元數據
    analysis_metadata: Dict[str, Any]
    # 計算時間戳
    computed_timestamp: str
    # 計算耗時 (秒)
    computation_time: float

@dataclass
class CacheStatistics:
    """快取統計資訊"""
    total_entries: int
    cache_hits: int
    cache_misses: int
    total_requests: int
    cache_file_size_mb: float
    last_updated: str

    @property
    def hit_rate(self) -> float:
        """快取命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests


class FragilityCacheManager:
    """
    易損性曲線快取管理器

    管理已計算的易損性曲線結果，提供高效的儲存、檢索和統計功能
    """

    def __init__(self, cache_file_path: str = "fragility_cache.json", worker_id: Optional[str] = None):
        """
        初始化快取管理器

        Args:
            cache_file_path: 快取檔案路徑
            worker_id: Worker ID，如果提供則使用獨立的cache檔案
        """
        # 設定 worker ID 和 cache 檔案路徑
        self.worker_id = worker_id
        self.is_main_worker = worker_id is None

        # 保存主 cache 檔案路徑（所有 worker 都需要知道）
        self.main_cache_file_path = Path(cache_file_path)

        if worker_id is not None:
            # Worker 使用獨立的 cache 檔案用於寫入
            cache_dir = Path(cache_file_path).parent
            cache_name = Path(cache_file_path).stem
            cache_ext = Path(cache_file_path).suffix
            worker_cache_name = f"{cache_name}_worker_{worker_id}{cache_ext}"
            self.cache_file_path = cache_dir / worker_cache_name

            logger.info(f"Worker {worker_id} initialized:")
            logger.info(f"  - Will READ from main cache: {self.main_cache_file_path}")
            logger.info(f"  - Will WRITE to worker cache: {self.cache_file_path}")
        else:
            # 主 worker 使用原始檔案名
            self.cache_file_path = Path(cache_file_path)
            logger.info(f"Main worker initialized with cache file: {self.cache_file_path}")
        self.cache_data: Dict[str, FragilityCurveResult] = {}
        self.stats = CacheStatistics(
            total_entries=0,
            cache_hits=0,
            cache_misses=0,
            total_requests=0,
            cache_file_size_mb=0.0,
            last_updated=""
        )

        # 執行緒鎖，確保快取操作的執行緒安全
        self._lock = threading.Lock()

        # 檔案鎖設定，確保多進程安全
        self._file_lock_timeout = 5.0  # 5秒超時
        self._file_lock_retry_delay = 0.1  # 100ms重試間隔
        self._max_lock_retries = 1  # 減少重試次數避免長時間等待
        self._use_file_locking = False  # 暫時禁用檔案鎖定以解決 WSL 兼容性問題

        # 載入現有的快取
        self.load_cache()

    def _generate_cache_key(self, archetype_code: str) -> str:
        """
        生成快取鍵值

        Args:
            archetype_code: 原型編碼

        Returns:
            str: 快取鍵值
        """
        # 使用原型編碼作為主要鍵值，確保一致性
        return archetype_code.strip().upper()

    def _safe_file_operation(self, operation_func, mode='r+', max_retries=None):
        """
        安全的檔案操作，包含檔案鎖和重試機制

        Args:
            operation_func: 要執行的檔案操作函數，接收檔案對象作為參數
            mode: 檔案開啟模式
            max_retries: 最大重試次數，預設使用實例配置

        Returns:
            操作函數的返回值
        """
        if max_retries is None:
            max_retries = self._max_lock_retries

        for attempt in range(max_retries + 1):
            try:
                # 確保快取目錄存在
                self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)

                # 開啟檔案並加鎖 - 使用 fcntl 進行檔案鎖定
                with open(self.cache_file_path, mode, encoding='utf-8') as f:
                    if self._use_file_locking:
                        try:
                            # 嘗試非阻塞鎖定（Unix/Linux 系統）
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                            result = operation_func(f)
                            return result
                        except (OSError, IOError) as lock_error:
                            # 如果鎖定失敗，等待一下再重試
                            if attempt < max_retries:
                                logger.debug(f"File locked by another process, retrying in {self._file_lock_retry_delay}s")
                                time.sleep(self._file_lock_retry_delay)
                                continue
                            else:
                                logger.warning(f"Could not acquire file lock after {max_retries + 1} attempts, proceeding without lock")
                                # 最後一次嘗試時，不使用鎖直接執行
                                result = operation_func(f)
                                return result
                        finally:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                            except:
                                pass  # 忽略解鎖錯誤
                    else:
                        # 檔案鎖定被禁用，直接執行操作
                        logger.debug("File locking disabled, executing operation without lock")
                        result = operation_func(f)
                        return result

            except FileNotFoundError:
                if 'r' in mode:
                    # 檔案不存在，這在首次執行時是正常的
                    logger.info("Cache file not found, starting with empty cache")
                    return None
                else:
                    # 寫入模式下建立新檔案
                    self.cache_file_path.touch()
                    continue
            except Exception as e:
                logger.error(f"Unexpected error during file operation: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(self._file_lock_retry_delay)

    def _create_backup(self) -> None:
        """建立快取檔案備份（使用 copy 而非 rename 以避免多進程競爭）"""
        if self.cache_file_path.exists():
            backup_path = self.cache_file_path.with_suffix(
                f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            try:
                # 使用 copy 而非 rename，確保原文件始終存在
                # 這樣可以避免其他 worker 在讀取時遇到 FileNotFoundError
                shutil.copy2(self.cache_file_path, backup_path)
                logger.info(f"Cache backup created: {backup_path}")

                # 只保留最新的5個備份檔案
                backup_dir = self.cache_file_path.parent
                backup_pattern = f"{self.cache_file_path.stem}.backup_*.json"
                backup_files = sorted(backup_dir.glob(backup_pattern))

                if len(backup_files) > 5:
                    for old_backup in backup_files[:-5]:
                        old_backup.unlink()
                        logger.debug(f"Removed old backup: {old_backup}")

            except Exception as e:
                logger.error(f"Failed to create backup: {e}")

    def load_cache(self) -> None:
        """載入快取檔案 - Worker 會先嘗試從主 cache 載入"""
        self.cache_data = {}
        loaded_from_main = False

        try:
            # Worker 優先從主 cache 載入已存在的結果
            if not self.is_main_worker and self.main_cache_file_path.exists():
                logger.info(f"Worker {self.worker_id}: Attempting to load from main cache: {self.main_cache_file_path}")

                # 增加重試機制以處理併發讀取問題
                max_retries = 3
                retry_delay = 0.1  # 100ms

                for attempt in range(max_retries):
                    try:
                        with open(self.main_cache_file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # 載入快取資料
                        cache_entries = data.get('cache_entries', {})

                        for key, entry_data in cache_entries.items():
                            try:
                                result = FragilityCurveResult(**entry_data)
                                self.cache_data[key] = result
                            except Exception as e:
                                logger.warning(f"Failed to load cache entry {key}: {e}")

                        logger.info(f"Worker {self.worker_id}: Successfully loaded {len(self.cache_data)} entries from main cache")
                        loaded_from_main = True
                        break  # 成功載入，跳出重試迴圈

                    except json.JSONDecodeError as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Worker {self.worker_id}: JSON decode error on attempt {attempt + 1}/{max_retries}: {e}")
                            logger.info(f"Worker {self.worker_id}: Retrying after {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            # 最後一次重試仍失敗
                            logger.warning(f"Worker {self.worker_id}: Failed to load main cache after {max_retries} attempts: {e}")
                            logger.info(f"Worker {self.worker_id}: Will start with empty cache")
                            break

                    except Exception as e:
                        # 其他類型的錯誤不重試
                        logger.warning(f"Worker {self.worker_id}: Failed to load main cache: {e}")
                        logger.info(f"Worker {self.worker_id}: Will start with empty cache")
                        break

            # 主 worker 或如果沒有主 cache，嘗試載入自己的 cache 檔案
            if not loaded_from_main and self.cache_file_path.exists():
                logger.info(f"Loading cache from: {self.cache_file_path}")

                # 增加重試機制以處理併發讀取問題
                max_retries = 3
                retry_delay = 0.1  # 100ms
                load_success = False

                for attempt in range(max_retries):
                    try:
                        with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # 載入快取資料
                        cache_entries = data.get('cache_entries', {})
                        self.cache_data = {}

                        for key, entry_data in cache_entries.items():
                            try:
                                result = FragilityCurveResult(**entry_data)
                                self.cache_data[key] = result
                            except Exception as e:
                                logger.warning(f"Failed to load cache entry {key}: {e}")

                        # 載入統計資料
                        stats_data = data.get('statistics', {})
                        self.stats = CacheStatistics(
                            total_entries=len(self.cache_data),
                            cache_hits=stats_data.get('cache_hits', 0),
                            cache_misses=stats_data.get('cache_misses', 0),
                            total_requests=stats_data.get('total_requests', 0),
                            cache_file_size_mb=self._get_file_size_mb(),
                            last_updated=stats_data.get('last_updated', datetime.now().isoformat())
                        )

                        logger.info(f"Loaded {len(self.cache_data)} entries from cache file: {self.cache_file_path}")
                        load_success = True
                        break  # 成功載入，跳出重試迴圈

                    except json.JSONDecodeError as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"JSON decode error on attempt {attempt + 1}/{max_retries}: {e}")
                            logger.info(f"Retrying after {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            # 最後一次重試仍失敗
                            logger.error(f"Failed to load cache after {max_retries} attempts: {e}")
                            logger.info("Starting with empty cache")
                            break

                    except Exception as e:
                        # 其他類型的錯誤不重試
                        logger.error(f"Failed to load cache: {e}")
                        logger.info("Starting with empty cache")
                        break

            elif not loaded_from_main:
                logger.info(f"No existing cache file found at {self.cache_file_path}, starting with empty cache")
                if not self.is_main_worker:
                    logger.info(f"Worker {self.worker_id}: Main cache also not found at {self.main_cache_file_path}")

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            logger.info("Starting with empty cache due to load failure")
            self.cache_data = {}

    def save_cache(self) -> None:
        """儲存快取檔案"""
        with self._lock:
            try:
                # 準備資料
                cache_entries = {}
                for key, result in self.cache_data.items():
                    cache_entries[key] = asdict(result)

                # 更新統計資料
                self.stats.total_entries = len(self.cache_data)
                self.stats.last_updated = datetime.now().isoformat()

                data = {
                    'version': '1.0',
                    'created_at': datetime.now().isoformat(),
                    'cache_entries': cache_entries,
                    'statistics': {
                        'total_entries': self.stats.total_entries,
                        'cache_hits': self.stats.cache_hits,
                        'cache_misses': self.stats.cache_misses,
                        'total_requests': self.stats.total_requests,
                        'hit_rate': self.stats.hit_rate,
                        'last_updated': self.stats.last_updated
                    }
                }

                # 確保目錄存在
                self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)

                # 建立備份 (如果檔案已存在)
                if self.cache_file_path.exists():
                    self._create_backup()

                # 直接寫入檔案（暫時跳過複雜的檔案鎖定）
                with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # 更新檔案大小統計
                self.stats.cache_file_size_mb = self._get_file_size_mb()

                logger.info(f"Cache saved with {len(self.cache_data)} entries "
                           f"({self.stats.cache_file_size_mb:.2f} MB)")

            except Exception as e:
                logger.error(f"Failed to save cache: {e}")
                raise

    def get_fragility_curve(self, archetype_code: str, check_updates: bool = False) -> Optional[FragilityCurveResult]:
        """
        獲取易損性曲線結果

        Args:
            archetype_code: 原型編碼
            check_updates: 是否檢查檔案更新（用於多進程同步）

        Returns:
            FragilityCurveResult: 易損性曲線結果，若不存在則返回None
        """
        with self._lock:
            self.stats.total_requests += 1
            cache_key = self._generate_cache_key(archetype_code)

            # 在多進程環境下，偶爾檢查檔案更新
            if check_updates and self.stats.total_requests % 50 == 0:
                self.reload_cache_if_modified()

            if cache_key in self.cache_data:
                self.stats.cache_hits += 1
                logger.debug(f"Cache hit for {archetype_code}")
                return self.cache_data[cache_key]
            else:
                # Cache miss - 在多進程環境下再檢查一次更新
                if check_updates:
                    if self.reload_cache_if_modified():
                        # 重新載入後再試一次
                        if cache_key in self.cache_data:
                            self.stats.cache_hits += 1
                            logger.debug(f"Cache hit after reload for {archetype_code}")
                            return self.cache_data[cache_key]

                self.stats.cache_misses += 1
                logger.debug(f"Cache miss for {archetype_code}")
                return None

    def store_fragility_curve(self, result: FragilityCurveResult) -> None:
        """
        儲存易損性曲線結果

        Args:
            result: 易損性曲線計算結果
        """
        with self._lock:
            cache_key = self._generate_cache_key(result.archetype_code)
            self.cache_data[cache_key] = result

            logger.info(f"Stored fragility curve for {result.archetype_code}")

            # 暫時禁用自動保存以避免遞歸問題
            # TODO: 重新啟用自動保存功能
            # if (len(self.cache_data) % 5 == 0 or
            #     self.stats.total_requests % 50 == 0):
            #     try:
            #         self.save_cache()
            #         logger.debug(f"Auto-saved cache with {len(self.cache_data)} entries")
            #     except Exception as e:
            #         logger.warning(f"Auto-save failed for {result.archetype_code}: {e}")
            #         # 自動儲存失敗不影響主要功能，只記錄警告

    def has_fragility_curve(self, archetype_code: str) -> bool:
        """
        檢查是否存在指定的易損性曲線

        Args:
            archetype_code: 原型編碼

        Returns:
            bool: 是否存在
        """
        cache_key = self._generate_cache_key(archetype_code)
        return cache_key in self.cache_data

    def get_cached_archetype_codes(self) -> List[str]:
        """
        獲取所有已快取的原型編碼

        Returns:
            list: 原型編碼列表
        """
        return list(self.cache_data.keys())

    def reload_cache_if_modified(self) -> bool:
        """
        如果檔案有更新則重新載入快取（用於多進程同步）

        Returns:
            bool: 是否重新載入了快取
        """
        try:
            if not self.cache_file_path.exists():
                return False

            # 檢查檔案修改時間
            current_mtime = self.cache_file_path.stat().st_mtime

            if not hasattr(self, '_last_cache_mtime'):
                self._last_cache_mtime = current_mtime
                return False

            if current_mtime > self._last_cache_mtime:
                logger.debug("Detected cache file modification, reloading...")
                old_count = len(self.cache_data)

                # 重新載入快取
                self.load_cache()
                self._last_cache_mtime = current_mtime

                new_count = len(self.cache_data)
                if new_count != old_count:
                    logger.info(f"Cache reloaded: {old_count} -> {new_count} entries")

                return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check cache modification: {e}")
            return False

    def get_cache_statistics(self) -> CacheStatistics:
        """
        獲取快取統計資訊

        Returns:
            CacheStatistics: 統計資訊
        """
        with self._lock:
            # 更新檔案大小
            self.stats.cache_file_size_mb = self._get_file_size_mb()
            self.stats.total_entries = len(self.cache_data)
            return self.stats

    def _get_file_size_mb(self) -> float:
        """獲取快取檔案大小 (MB)"""
        try:
            if self.cache_file_path.exists():
                size_bytes = self.cache_file_path.stat().st_size
                return size_bytes / (1024 * 1024)
            return 0.0
        except Exception:
            return 0.0

    def clear_cache(self) -> None:
        """清空快取"""
        with self._lock:
            self.cache_data.clear()
            self.stats = CacheStatistics(
                total_entries=0,
                cache_hits=0,
                cache_misses=0,
                total_requests=0,
                cache_file_size_mb=0.0,
                last_updated=datetime.now().isoformat()
            )
            logger.info("Cache cleared")

    def remove_entry(self, archetype_code: str) -> bool:
        """
        移除指定的快取項目

        Args:
            archetype_code: 原型編碼

        Returns:
            bool: 是否成功移除
        """
        with self._lock:
            cache_key = self._generate_cache_key(archetype_code)
            if cache_key in self.cache_data:
                del self.cache_data[cache_key]
                logger.info(f"Removed cache entry for {archetype_code}")
                return True
            return False

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """
        清理過期的快取項目

        Args:
            max_age_days: 最大保存天數

        Returns:
            int: 清理的項目數量
        """
        with self._lock:
            current_time = datetime.now()
            removed_count = 0

            entries_to_remove = []
            for key, result in self.cache_data.items():
                try:
                    computed_time = datetime.fromisoformat(result.computed_timestamp)
                    age_days = (current_time - computed_time).days

                    if age_days > max_age_days:
                        entries_to_remove.append(key)
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp for {key}: {e}")
                    # 如果時間戳無效，也標記為移除
                    entries_to_remove.append(key)

            for key in entries_to_remove:
                del self.cache_data[key]
                removed_count += 1

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old cache entries")

            return removed_count

    def export_statistics(self) -> Dict[str, Any]:
        """
        匯出詳細的統計資訊

        Returns:
            dict: 詳細統計資訊
        """
        stats = self.get_cache_statistics()

        # 分析原型編碼分佈
        structural_systems = {}
        construction_eras = {}
        floor_counts = {}
        area_scales = {}

        for code in self.cache_data.keys():
            try:
                parts = code.split('-')
                if len(parts) >= 4:
                    system = parts[0]
                    era = parts[1]
                    floor = parts[2]
                    area = parts[3]

                    structural_systems[system] = structural_systems.get(system, 0) + 1
                    construction_eras[era] = construction_eras.get(era, 0) + 1
                    floor_counts[floor] = floor_counts.get(floor, 0) + 1
                    area_scales[area] = area_scales.get(area, 0) + 1
            except Exception:
                pass

        return {
            'basic_statistics': asdict(stats),
            'archetype_distribution': {
                'structural_systems': structural_systems,
                'construction_eras': construction_eras,
                'floor_counts': floor_counts,
                'area_scales': area_scales
            },
            'cache_file_path': str(self.cache_file_path),
            'export_timestamp': datetime.now().isoformat()
        }

    def merge_worker_caches(self, base_cache_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        合併所有worker的cache檔案到主cache中（僅主worker可調用）

        Args:
            base_cache_dir: 搜尋worker cache檔案的目錄，預設為當前cache檔案目錄

        Returns:
            dict: 合併統計資訊
        """
        if not self.is_main_worker:
            raise ValueError("只有主worker可以執行cache合併操作")

        if base_cache_dir is None:
            base_cache_dir = self.cache_file_path.parent
        else:
            base_cache_dir = Path(base_cache_dir)

        # 查找所有worker cache檔案
        cache_pattern = f"{self.cache_file_path.stem}_worker_*.json"
        worker_cache_files = list(base_cache_dir.glob(cache_pattern))

        merged_count = 0
        new_entries = 0
        updated_entries = 0

        logger.info(f"Finding worker cache files: {cache_pattern}")
        logger.info(f"Found {len(worker_cache_files)} worker cache files")

        for worker_cache_file in worker_cache_files:
            try:
                logger.debug(f"Merging cache from: {worker_cache_file}")

                # 讀取worker cache檔案
                with open(worker_cache_file, 'r', encoding='utf-8') as f:
                    worker_data = json.load(f)

                worker_cache_entries = worker_data.get('cache_entries', {})

                # 合併cache entries（聯集操作）
                for key, entry_data in worker_cache_entries.items():
                    try:
                        result = FragilityCurveResult(**entry_data)

                        if key in self.cache_data:
                            # 檢查是否需要更新（比較時間戳）
                            existing_time = datetime.fromisoformat(self.cache_data[key].computed_timestamp)
                            new_time = datetime.fromisoformat(result.computed_timestamp)

                            if new_time > existing_time:
                                self.cache_data[key] = result
                                updated_entries += 1
                                logger.debug(f"Updated cache entry: {key}")
                        else:
                            # 新的cache項目
                            self.cache_data[key] = result
                            new_entries += 1
                            logger.debug(f"Added new cache entry: {key}")

                    except Exception as e:
                        logger.warning(f"Failed to merge cache entry {key}: {e}")

                merged_count += 1

            except Exception as e:
                logger.error(f"Failed to merge worker cache {worker_cache_file}: {e}")

        # 更新統計資訊
        self.stats.total_entries = len(self.cache_data)
        self.stats.last_updated = datetime.now().isoformat()

        merge_stats = {
            'worker_files_found': len(worker_cache_files),
            'worker_files_merged': merged_count,
            'new_entries_added': new_entries,
            'entries_updated': updated_entries,
            'total_entries_after_merge': len(self.cache_data)
        }

        logger.info(f"Cache merge completed: {merge_stats}")
        return merge_stats

    def cleanup_worker_cache_files(self, base_cache_dir: Optional[str] = None) -> int:
        """
        清理worker cache檔案（僅主worker可調用）

        Args:
            base_cache_dir: 搜尋worker cache檔案的目錄，預設為當前cache檔案目錄

        Returns:
            int: 清理的檔案數量
        """
        if not self.is_main_worker:
            raise ValueError("只有主worker可以執行cache檔案清理操作")

        if base_cache_dir is None:
            base_cache_dir = self.cache_file_path.parent
        else:
            base_cache_dir = Path(base_cache_dir)

        # 查找所有worker cache檔案
        cache_pattern = f"{self.cache_file_path.stem}_worker_*.json"
        worker_cache_files = list(base_cache_dir.glob(cache_pattern))

        cleaned_count = 0

        for worker_cache_file in worker_cache_files:
            try:
                worker_cache_file.unlink()
                cleaned_count += 1
                logger.debug(f"Cleaned worker cache file: {worker_cache_file}")
            except Exception as e:
                logger.warning(f"Failed to clean worker cache file {worker_cache_file}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} worker cache files")

        return cleaned_count


def test_fragility_cache():
    """測試易損性快取管理器"""
    import tempfile
    import os

    # 建立臨時快取檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_cache_file = f.name

    try:
        print("Testing Fragility Cache Manager...")

        # 初始化快取管理器
        cache_manager = FragilityCacheManager(temp_cache_file)

        # 建立測試結果
        test_result = FragilityCurveResult(
            archetype_code="RC-PRE-5F-S",
            collapse_probabilities={
                '3': 0.001,
                '4': 0.005,
                '5': 0.02,
                '6': 0.1,
                '7': 0.3
            },
            analysis_metadata={
                'ground_motions_used': 20,
                'analysis_type': 'IDA',
                'damping_ratio': 0.05
            },
            computed_timestamp=datetime.now().isoformat(),
            computation_time=120.5
        )

        # 測試儲存
        cache_manager.store_fragility_curve(test_result)
        print(f"Stored result for {test_result.archetype_code}")

        # 測試檢索
        retrieved = cache_manager.get_fragility_curve("RC-PRE-5F-S")
        if retrieved:
            print(f"Retrieved result: {retrieved.collapse_probabilities}")
        else:
            print("Failed to retrieve result")

        # 測試快取命中/未命中
        print(f"Cache hit: {cache_manager.has_fragility_curve('RC-PRE-5F-S')}")
        print(f"Cache miss: {cache_manager.has_fragility_curve('SC-POST-10F-L')}")

        # 儲存並顯示統計
        cache_manager.save_cache()
        stats = cache_manager.get_cache_statistics()
        print(f"\nStatistics:")
        print(f"Total entries: {stats.total_entries}")
        print(f"Hit rate: {stats.hit_rate:.2%}")
        print(f"File size: {stats.cache_file_size_mb:.2f} MB")

    finally:
        # 清理臨時檔案
        if os.path.exists(temp_cache_file):
            os.unlink(temp_cache_file)


if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    # 執行測試
    test_fragility_cache()