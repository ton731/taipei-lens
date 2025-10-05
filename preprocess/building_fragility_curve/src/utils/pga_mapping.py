#!/usr/bin/env python3
"""
PGA Seismic Intensity Mapping Module

此模組負責將Peak Ground Acceleration (PGA)值對應到台灣中央氣象局的震度階級，
並提供易損性曲線分析所需的強度對應功能。

根據PRD定義的震度階級與PGA對應關係：
- 3級: 8-25 cm/sec²
- 4級: 25-80 cm/sec²
- 5弱: 80-140 cm/sec²
- 5強: 140-250 cm/sec²
- 6弱: 250-440 cm/sec²
- 6強: 440-800 cm/sec²
- 7級: >800 cm/sec²
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SeismicIntensity:
    """地震強度級別定義"""
    level: str              # 震度級別名稱
    pga_min: float         # PGA下限 (cm/s²)
    pga_max: float         # PGA上限 (cm/s²)
    representative_pga: float  # 代表性PGA值


class PGAIntensityMapper:
    """
    PGA與震度強度對應器

    提供PGA值與震度級別之間的雙向轉換功能
    """

    def __init__(self):
        """初始化震度級別定義"""
        self.intensity_levels = {
            '3': SeismicIntensity(
                level='3',
                pga_min=8.0,
                pga_max=25.0,
                representative_pga=16.5  # 幾何平均
            ),
            '4': SeismicIntensity(
                level='4',
                pga_min=25.0,
                pga_max=80.0,
                representative_pga=44.7  # 幾何平均
            ),
            '5弱': SeismicIntensity(
                level='5弱',
                pga_min=80.0,
                pga_max=140.0,
                representative_pga=105.8  # 幾何平均
            ),
            '5強': SeismicIntensity(
                level='5強',
                pga_min=140.0,
                pga_max=250.0,
                representative_pga=187.1  # 幾何平均
            ),
            '6弱': SeismicIntensity(
                level='6弱',
                pga_min=250.0,
                pga_max=440.0,
                representative_pga=331.7  # 幾何平均
            ),
            '6強': SeismicIntensity(
                level='6強',
                pga_min=440.0,
                pga_max=800.0,
                representative_pga=592.8  # 幾何平均
            ),
            '7': SeismicIntensity(
                level='7',
                pga_min=800.0,
                pga_max=2000.0,  # 設定合理的上限
                representative_pga=1265.0  # 幾何平均
            )
        }

        # 建立有序的PGA閾值列表，用於快速查找
        self.pga_thresholds = sorted([
            (level_data.pga_min, level)
            for level, level_data in self.intensity_levels.items()
        ])

    def pga_to_intensity_level(self, pga: float) -> Optional[str]:
        """
        將PGA值轉換為震度級別

        Args:
            pga: Peak Ground Acceleration (cm/s²)

        Returns:
            str: 震度級別，如果PGA太低則返回None
        """
        if pga < 8.0:  # 低於3級的最小值
            return None

        for level, level_data in self.intensity_levels.items():
            if level_data.pga_min <= pga < level_data.pga_max:
                return level

        # 如果超過最高級別的上限，返回7級
        if pga >= self.intensity_levels['7'].pga_min:
            return '7'

        return None

    def intensity_level_to_pga(self, level: str) -> float:
        """
        將震度級別轉換為代表性PGA值

        Args:
            level: 震度級別

        Returns:
            float: 代表性PGA值 (cm/s²)

        Raises:
            ValueError: 如果級別不存在
        """
        if level not in self.intensity_levels:
            raise ValueError(f"Unknown intensity level: {level}")

        return self.intensity_levels[level].representative_pga

    def get_pga_range(self, level: str) -> Tuple[float, float]:
        """
        獲取指定震度級別的PGA範圍

        Args:
            level: 震度級別

        Returns:
            tuple: (PGA最小值, PGA最大值)

        Raises:
            ValueError: 如果級別不存在
        """
        if level not in self.intensity_levels:
            raise ValueError(f"Unknown intensity level: {level}")

        level_data = self.intensity_levels[level]
        return level_data.pga_min, level_data.pga_max

    def get_all_target_levels(self) -> List[str]:
        """
        獲取所有目標震度級別

        Returns:
            list: 震度級別列表，按強度排序
        """
        return ['3', '4', '5弱', '5強', '6弱', '6強', '7']

    def get_target_pga_values(self) -> Dict[str, float]:
        """
        獲取所有目標震度級別的代表性PGA值

        Returns:
            dict: 震度級別對應的PGA值字典
        """
        return {
            level: level_data.representative_pga
            for level, level_data in self.intensity_levels.items()
        }

    def interpolate_collapse_probability(self, pga_values: np.ndarray,
                                       collapse_probs: np.ndarray,
                                       target_level: str) -> float:
        """
        插值計算指定震度級別的倒塌機率

        Args:
            pga_values: 分析得到的PGA值陣列 (cm/s²)
            collapse_probs: 對應的倒塌機率陣列
            target_level: 目標震度級別

        Returns:
            float: 插值得到的倒塌機率

        Raises:
            ValueError: 如果資料不足或級別不存在
        """
        if target_level not in self.intensity_levels:
            raise ValueError(f"Unknown intensity level: {target_level}")

        target_pga = self.intensity_levels[target_level].representative_pga

        # 確保輸入陣列有效
        if len(pga_values) != len(collapse_probs):
            raise ValueError("PGA values and collapse probabilities must have same length")

        if len(pga_values) < 2:
            raise ValueError("Need at least 2 data points for interpolation")

        # 排序資料
        sorted_indices = np.argsort(pga_values)
        sorted_pga = pga_values[sorted_indices]
        sorted_probs = collapse_probs[sorted_indices]

        # 確保機率在合理範圍內
        sorted_probs = np.clip(sorted_probs, 0.0, 1.0)

        # 執行線性插值
        try:
            if target_pga <= sorted_pga[0]:
                # 外插到較低值
                interpolated_prob = sorted_probs[0]
            elif target_pga >= sorted_pga[-1]:
                # 外插到較高值
                interpolated_prob = sorted_probs[-1]
            else:
                # 內插
                interpolated_prob = np.interp(target_pga, sorted_pga, sorted_probs)

            # 確保結果在合理範圍內
            interpolated_prob = float(np.clip(interpolated_prob, 0.0, 1.0))

            logger.debug(f"Interpolated collapse probability for level {target_level} "
                        f"(PGA={target_pga:.1f}): {interpolated_prob:.6f}")

            return interpolated_prob

        except Exception as e:
            logger.error(f"Interpolation failed for level {target_level}: {e}")
            # 返回保守的估計值
            if target_pga <= np.median(sorted_pga):
                return float(np.min(sorted_probs))
            else:
                return float(np.max(sorted_probs))

    def create_fragility_curve_dict(self, pga_values: np.ndarray,
                                   collapse_probs: np.ndarray) -> Dict[str, float]:
        """
        建立完整的易損性曲線字典

        為所有目標震度級別計算倒塌機率

        Args:
            pga_values: 分析得到的PGA值陣列 (cm/s²)
            collapse_probs: 對應的倒塌機率陣列

        Returns:
            dict: 震度級別對應倒塌機率的字典
        """
        fragility_curve = {}

        for level in self.get_all_target_levels():
            try:
                prob = self.interpolate_collapse_probability(
                    pga_values, collapse_probs, level
                )
                fragility_curve[level] = prob
            except Exception as e:
                logger.warning(f"Failed to compute probability for level {level}: {e}")
                # 使用保守的預設值
                if level in ['3', '4']:
                    fragility_curve[level] = 0.0
                elif level in ['5弱', '5強']:
                    fragility_curve[level] = 0.01
                elif level in ['6弱', '6強']:
                    fragility_curve[level] = 0.1
                else:  # 7級
                    fragility_curve[level] = 0.3

        return fragility_curve

    def validate_fragility_curve(self, fragility_curve: Dict[str, float]) -> bool:
        """
        驗證易損性曲線的合理性

        檢查機率是否遞增，數值是否在合理範圍內

        Args:
            fragility_curve: 易損性曲線字典

        Returns:
            bool: 是否通過驗證
        """
        try:
            levels = self.get_all_target_levels()
            prev_prob = 0.0

            for level in levels:
                if level not in fragility_curve:
                    logger.error(f"Missing probability for level {level}")
                    return False

                prob = fragility_curve[level]

                # 檢查數值範圍
                if not (0.0 <= prob <= 1.0):
                    logger.error(f"Probability for level {level} out of range: {prob}")
                    return False

                # 檢查遞增性 (允許小幅波動)
                if prob < prev_prob - 0.01:  # 允許1%的向下波動
                    logger.warning(f"Non-monotonic behavior at level {level}: "
                                 f"{prev_prob} -> {prob}")

                prev_prob = prob

            return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    def get_intensity_statistics(self) -> Dict:
        """
        獲取震度級別統計資訊

        Returns:
            dict: 統計資訊字典
        """
        stats = {
            'total_levels': len(self.intensity_levels),
            'pga_range': {
                'min': min(level.pga_min for level in self.intensity_levels.values()),
                'max': max(level.pga_max for level in self.intensity_levels.values())
            },
            'levels': {}
        }

        for level, level_data in self.intensity_levels.items():
            stats['levels'][level] = {
                'pga_min': level_data.pga_min,
                'pga_max': level_data.pga_max,
                'representative_pga': level_data.representative_pga,
                'pga_range_ratio': level_data.pga_max / level_data.pga_min
            }

        return stats


def test_pga_intensity_mapper():
    """測試PGA強度對應器"""
    mapper = PGAIntensityMapper()

    print("Testing PGA Intensity Mapper...")

    # 測試PGA到震度級別的轉換
    test_pga_values = [15, 50, 120, 200, 350, 600, 1000]

    print("\nPGA to Intensity Level:")
    for pga in test_pga_values:
        level = mapper.pga_to_intensity_level(pga)
        print(f"PGA {pga:4.0f} cm/s² -> Level {level}")

    # 測試震度級別到PGA的轉換
    print("\nIntensity Level to Representative PGA:")
    for level in mapper.get_all_target_levels():
        pga = mapper.intensity_level_to_pga(level)
        pga_min, pga_max = mapper.get_pga_range(level)
        print(f"Level {level:2} -> PGA {pga:6.1f} cm/s² (range: {pga_min:.0f}-{pga_max:.0f})")

    # 測試插值功能
    print("\nTesting Interpolation:")
    test_pga_array = np.array([10, 30, 100, 200, 400, 700, 1200])
    test_probs = np.array([0.001, 0.005, 0.02, 0.08, 0.25, 0.45, 0.70])

    fragility_curve = mapper.create_fragility_curve_dict(test_pga_array, test_probs)

    print("Fragility Curve:")
    for level in mapper.get_all_target_levels():
        prob = fragility_curve[level]
        print(f"Level {level:2}: {prob:.4f}")

    # 驗證結果
    is_valid = mapper.validate_fragility_curve(fragility_curve)
    print(f"\nFragility curve validation: {'PASSED' if is_valid else 'FAILED'}")


if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    # 執行測試
    test_pga_intensity_mapper()