#!/usr/bin/env python3
"""
Archetype Parameter Generator Module

此模組負責根據PRD中定義的原型參數表格，為每個建築分類生成詳細的結構參數，
並轉換為Stick Model所需的力學參數 (Ke, Fy, α)。

功能包括：
1. RC結構參數生成與轉換
2. SC結構參數生成與轉換
3. 從建築面積估算柱數量和質量
4. 生成完整的Stick Model參數
"""

import math
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from building_classifier import BuildingProperties

logger = logging.getLogger(__name__)

@dataclass
class StoryParameters:
    """單層結構參數"""
    story: int
    mass: float           # 樓層質量 (kgf·s²/cm)
    k: float             # 樓層剪力剛度 (kgf/cm)
    Fy: float            # 降伏強度 (kgf)
    alpha: float         # 硬化比
    story_height: float  # 樓層高度 (cm)
    material_type: str   # 材料類型 ('steel', 'concrete')

@dataclass
class StickModelParameters:
    """完整的Stick Model參數"""
    building_id: str
    archetype_code: str
    stories: List[StoryParameters] = field(default_factory=list)
    total_height: float = 0.0
    total_mass: float = 0.0


class ArchetypeParameterGenerator:
    """
    原型參數生成器

    根據PRD定義的原型參數表格，生成結構分析所需的詳細參數
    """

    def __init__(self):
        # 材料參數
        self.concrete_E_factor = 15000  # Ec ≈ 15000 * sqrt(fc')
        self.steel_E = 2.04e6          # 鋼材彈性模數 (kgf/cm²)

        # 典型樓層高度 (cm)
        self.typical_story_height = 350.0  # 3.5m

        # 單位面積重量 (kgf/m²)
        self.unit_weight_per_sqm = 1000.0  # 1.0 tf/m² = 1000 kgf/m²

        # RC結構原型參數表 (PRD表4.1)
        self.rc_parameters = self._initialize_rc_parameters()

        # SC結構原型參數表 (PRD表4.2)
        self.sc_parameters = self._initialize_sc_parameters()

    def _get_material_type(self, structural_system: str) -> str:
        """
        將結構系統代碼映射到材料類型

        Args:
            structural_system: 結構系統代碼 ('RC' 或 'SC')

        Returns:
            str: 材料類型 ('concrete' 或 'steel')
        """
        if structural_system == 'RC':
            return 'concrete'
        elif structural_system == 'SC':
            return 'steel'
        else:
            logger.warning(f"Unknown structural system: {structural_system}, defaulting to concrete")
            return 'concrete'

    def _initialize_rc_parameters(self) -> Dict:
        """初始化RC結構參數表"""
        return {
            'PRE': {
                'low': {  # 1-7層
                    'ranges': [(7, 7), (3, 6), (1, 2)],
                    'sections': [(40, 40), (45, 45), (50, 50)],
                    'fc_prime': [150, 150, 150],
                    'fy': [2800, 2800, 2800],
                    'rho_g': [0.01, 0.015, 0.015],
                    'alpha': 0.001
                },
                'mid': {  # 8-14層
                    'ranges': [(11, 14), (5, 10), (1, 4)],
                    'sections': [(50, 50), (60, 60), (70, 70)],
                    'fc_prime': [150, 150, 150],
                    'fy': [2800, 2800, 2800],
                    'rho_g': [0.015, 0.02, 0.022],
                    'alpha': 0.001
                },
                'high': {  # 15+層
                    'ranges': [(11, 999), (6, 10), (1, 5)],
                    'sections': [(60, 60), (75, 75), (90, 90)],
                    'fc_prime': [175, 175, 175],
                    'fy': [2800, 2800, 2800],
                    'rho_g': [0.02, 0.02, 0.025],
                    'alpha': 0.001
                },
                # 'very_high': {  # 20+層
                #     'ranges': [(20, 999), (8, 19), (1, 7)],
                #     'sections': [(70, 70), (90, 90), (120, 120)],
                #     'fc_prime': [350, 420, 420],
                #     'fy': [4200, 4200, 4200],
                #     'rho_g': [0.025, 0.025, 0.025],
                #     'alpha': 0.02
                # }
                'very_high': {  # 20+層
                    'ranges': [(20, 999), (8, 19), (1, 7)],
                    'sections': [(70, 70), (90, 90), (120, 120)],
                    'fc_prime': [180, 180, 180],
                    'fy': [2800, 2800, 2800],
                    'rho_g': [0.02, 0.02, 0.025],
                    'alpha': 0.001
                }
            },
            'POST': {
                'low': {  # 1-7層
                    'ranges': [(7, 7), (3, 6), (1, 2)],
                    'sections': [(40, 40), (45, 45), (50, 50)],
                    'fc_prime': [210, 210, 210],
                    'fy': [4200, 4200, 4200],
                    'rho_g': [0.01, 0.015, 0.015],
                    'alpha': 0.02
                },
                'mid': {  # 8-14層
                    'ranges': [(11, 14), (5, 10), (1, 4)],
                    'sections': [(50, 50), (60, 60), (70, 70)],
                    'fc_prime': [280, 280, 280],
                    'fy': [4200, 4200, 4200],
                    'rho_g': [0.018, 0.02, 0.022],
                    'alpha': 0.02
                },
                'high': {  # 15+層
                    'ranges': [(11, 999), (6, 10), (1, 5)],
                    'sections': [(60, 60), (75, 75), (90, 90)],
                    'fc_prime': [280, 350, 350],
                    'fy': [4200, 4200, 4200],
                    'rho_g': [0.02, 0.025, 0.025],
                    'alpha': 0.02
                },
                'very_high': {  # 20+層
                    'ranges': [(20, 999), (8, 19), (1, 7)],
                    'sections': [(70, 70), (90, 90), (120, 120)],
                    'fc_prime': [350, 420, 420],
                    'fy': [4200, 4200, 4200],
                    'rho_g': [0.025, 0.025, 0.025],
                    'alpha': 0.02
                }
            }
        }

    def _initialize_sc_parameters(self) -> Dict:
        """初始化SC結構參數表"""
        return {
            'PRE': {
                'low': {  # 1-5層
                    'ranges': [(5, 5), (3, 4), (1, 2)],
                    'column_Ix': [18400, 34800, 57900],
                    'column_Zx': [1320, 2150, 3140],
                    'beam_Ix': [19800, 29600, 42800],
                    'beam_Zx': [1080, 1420, 1840],
                    'fy': [2400, 2400, 2400],
                    'alpha': 0.001
                },
                'mid': {  # 5-12層
                    'ranges': [(11, 12), (7, 10), (4, 6), (1, 3)],
                    'column_Ix': [57900, 81500, 134000, 241000],
                    'column_Zx': [3140, 3950, 5880, 9900],
                    'beam_Ix': [59100, 115000, 136000, 136000],
                    'beam_Zx': [2110, 3780, 4180, 4180],
                    'fy': [3200, 3200, 3200, 3200],
                    'alpha': 0.001
                },
                'high': {  # 12+層
                    'ranges': [(12, 999), (8, 11), (5, 7), (1, 4)],
                    'column_Ix': [134000, 241000, 360000, 360000],
                    'column_Zx': [5880, 9900, 13200, 13200],
                    'beam_Ix': [136000, 182000, 268000, 268000],
                    'beam_Zx': [4180, 4910, 6460, 6460],
                    'fy': [3200, 3200, 3200, 3250],
                    'alpha': 0.001
                }

            },
            'POST': {
                'low': {  # 1-5層
                    'ranges': [(5, 5), (3, 4), (1, 2)],
                    'column_Ix': [18400, 34800, 57900],
                    'column_Zx': [1320, 2150, 3140],
                    'beam_Ix': [19800, 29600, 42800],
                    'beam_Zx': [1080, 1420, 1840],
                    'fy': [3250, 3250, 3250],
                    'alpha': 0.025
                },
                'mid': {  # 5-12層
                    'ranges': [(11, 12), (7, 10), (4, 6), (1, 3)],
                    'column_Ix': [57900, 81500, 134000, 241000],
                    'column_Zx': [3140, 3950, 5880, 9900],
                    'beam_Ix': [59100, 115000, 136000, 136000],
                    'beam_Zx': [2110, 3780, 4180, 4180],
                    'fy': [3250, 3250, 3250, 3250],
                    'alpha': 0.025
                },
                'high': {  # 12+層
                    'ranges': [(12, 999), (8, 11), (5, 7), (1, 4)],
                    'column_Ix': [134000, 241000, 360000, 360000],
                    'column_Zx': [5880, 9900, 13200, 13200],
                    'beam_Ix': [136000, 182000, 268000, 268000],
                    'beam_Zx': [4180, 4910, 6460, 6460],
                    'fy': [3250, 3250, 3250, 3250],
                    'alpha': 0.025
                }
            }
        }

    def estimate_column_count(self, area_sqm: float, area_scale: str) -> int:
        """
        估算柱數量

        根據建築面積和規模估算柱子數量
        """
        # 基於典型結構佈置的經驗公式
        if area_scale == 'S':      # 小型建築 < 150 m²
            # 小型建築通常為簡單矩形平面，柱距約6-8m
            column_count = max(4, int(area_sqm / 30))
        elif area_scale == 'M':    # 中型建築 150-500 m²
            # 中型建築柱距約8-10m
            column_count = max(6, int(area_sqm / 40))
        else:                      # 大型建築 > 500 m²
            # 大型建築柱距約10-12m
            column_count = max(8, int(area_sqm / 50))

        return column_count

    def get_rc_story_parameters(self, building_props: BuildingProperties,
                               story: int) -> Tuple[float, float, float]:
        """
        獲取RC結構指定樓層的材料參數

        Returns:
            tuple: (斷面寬度, 斷面高度, fc', fy, rho_g, alpha)
        """
        era = building_props.construction_era
        floor_count = building_props.floor_count

        # 選擇高度類別
        if floor_count <= 7:
            height_category = 'low'
        elif floor_count <= 14:
            height_category = 'mid'
        elif floor_count <= 19:
            height_category = 'high'
        else:  # 20+ floors
            height_category = 'very_high'

        logger.info(f"floor_count: {floor_count}, story: {story}, RC height category: {height_category}")
        params = self.rc_parameters[era][height_category]

        # 根據樓層找到對應的參數組
        for i, (floor_min, floor_max) in enumerate(params['ranges']):
            if floor_min <= story <= floor_max:
                b, h = params['sections'][i]
                fc_prime = params['fc_prime'][i]
                fy = params['fy'][i]
                rho_g = params['rho_g'][i]
                alpha = params['alpha']
                # Validate alpha for OpenSees compatibility
                if alpha < 0:
                    raise ValueError(f"Alpha value must be >= 0 for OpenSees compatibility, got {alpha}")
                return b, h, fc_prime, fy, rho_g, alpha

        # 如果沒找到，使用最底層參數
        i = len(params['ranges']) - 1
        b, h = params['sections'][i]
        fc_prime = params['fc_prime'][i]
        fy = params['fy'][i]
        rho_g = params['rho_g'][i]
        alpha = params['alpha']
        # Validate alpha for OpenSees compatibility
        if alpha < 0:
            raise ValueError(f"Alpha value must be >= 0 for OpenSees compatibility, got {alpha}")
        return b, h, fc_prime, fy, rho_g, alpha

    def calculate_rc_story_parameters(self, building_props: BuildingProperties,
                                    story: int) -> StoryParameters:
        """
        計算RC結構單層參數

        根據PRD 5.1節的轉換流程計算
        """
        # 獲取材料參數
        b, h, fc_prime, fy, rho_g, alpha = self.get_rc_story_parameters(
            building_props, story)

        # 估算柱數量 - 使用代表性面積
        column_count = self.estimate_column_count(
            building_props.representative_area_sqm, building_props.area_scale)

        # 計算單柱斷面性質
        Ic = (b * h**3) / 12  # 慣性矩 (cm⁴)

        # 計算降伏彎矩
        if rho_g is not None:
            Ast = rho_g * b * h  # 主筋總面積 (cm²)
            My = 0.8 * Ast * fy * h  # 降伏彎矩 (kgf·cm)
        else:
            # 如果沒有鋼筋比，使用經驗估算
            My = 0.1 * b * h**2 * fc_prime  # 簡化估算

        # 計算單柱側向力學性質
        H = self.typical_story_height  # 樓層高度 (cm)
        Ec = self.concrete_E_factor * math.sqrt(fc_prime)  # 混凝土彈性模數

        kc = (12 * Ec * Ic) / (H**3)  # 單柱側向勁度 (kgf/cm)
        Vy = (2 * My) / H  # 單柱降伏剪力 (kgf)

        # 疊加樓層參數
        Ke = column_count * kc  # 樓層勁度 (kgf/cm)
        Fy = column_count * Vy  # 樓層降伏強度 (kgf)

        # 計算樓層質量 - 使用代表性面積
        floor_mass = (self.unit_weight_per_sqm * building_props.representative_area_sqm) / 980.665
        # 轉換為 kgf·s²/cm (重量/重力加速度)

        # 驗證質量計算結果
        if not self._validate_mass_calculation(floor_mass, building_props, story):
            # 使用最小安全質量值
            floor_mass = max(floor_mass, self._get_minimum_safe_mass(building_props))

        return StoryParameters(
            story=story,
            mass=floor_mass,
            k=Ke,
            Fy=Fy,
            alpha=alpha,
            story_height=H,
            material_type=self._get_material_type(building_props.structural_system)
        )

    def get_sc_story_parameters(self, building_props: BuildingProperties,
                               story: int) -> Tuple[float, float, float, float, float]:
        """
        獲取SC結構指定樓層的斷面參數

        Returns:
            tuple: (column_Ix, column_Zx, beam_Ix, beam_Zx, fy, alpha)
        """
        era = building_props.construction_era
        floor_count = building_props.floor_count

        # 選擇高度類別 (SC結構參數表較簡單)
        if floor_count <= 5:
            height_category = 'low'
        elif floor_count <= 11:
            height_category = 'mid'
        else:  # 12+ floors
            height_category = 'high'

        # 如果沒有對應的高度類別，使用mid
        if height_category not in self.sc_parameters[era]:
            height_category = 'mid'

        params = self.sc_parameters[era][height_category]

        # 根據樓層找到對應的參數組
        for i, (floor_min, floor_max) in enumerate(params['ranges']):
            if floor_min <= story <= floor_max:
                column_Ix = params['column_Ix'][i]
                column_Zx = params['column_Zx'][i]
                beam_Ix = params['beam_Ix'][i]
                beam_Zx = params['beam_Zx'][i]
                fy = params['fy'][i]
                alpha = params['alpha']
                # Validate alpha for OpenSees compatibility
                if alpha < 0:
                    raise ValueError(f"Alpha value must be >= 0 for OpenSees compatibility, got {alpha}")
                return column_Ix, column_Zx, beam_Ix, beam_Zx, fy, alpha

        # 如果沒找到，使用最底層參數
        i = len(params['ranges']) - 1
        column_Ix = params['column_Ix'][i]
        column_Zx = params['column_Zx'][i]
        beam_Ix = params['beam_Ix'][i]
        beam_Zx = params['beam_Zx'][i]
        fy = params['fy'][i]
        alpha = params['alpha']
        # Validate alpha for OpenSees compatibility
        if alpha < 0:
            raise ValueError(f"Alpha value must be >= 0 for OpenSees compatibility, got {alpha}")
        return column_Ix, column_Zx, beam_Ix, beam_Zx, fy, alpha

    def calculate_sc_story_parameters(self, building_props: BuildingProperties,
                                    story: int) -> StoryParameters:
        """
        計算SC結構單層參數

        根據PRD 5.2節的轉換流程計算
        """
        # 獲取斷面參數
        column_Ix, column_Zx, beam_Ix, beam_Zx, fy, alpha = \
            self.get_sc_story_parameters(building_props, story)

        # 估算構件數量 - 使用代表性面積
        column_count = self.estimate_column_count(
            building_props.representative_area_sqm, building_props.area_scale)
        beam_count = column_count  # 簡化假設梁數等於柱數

        # 計算樓層等效參數
        H = self.typical_story_height  # 樓層高度 (cm)
        L = math.sqrt(building_props.representative_area_sqm * 10000) / 2  # 估算梁跨度 (cm) - 使用代表性面積

        # 樓層勁度 (由柱子貢獻)
        Ke = column_count * (12 * self.steel_E * column_Ix) / (H**3)

        # 樓層降伏強度 (由梁端塑性鉸決定)
        Mp = fy * beam_Zx  # 梁的塑性彎矩 (kgf·cm)
        Fy = beam_count * (2 * Mp) / L  # 樓層降伏強度 (kgf)

        # 計算樓層質量 - 使用代表性面積
        floor_mass = (self.unit_weight_per_sqm * building_props.representative_area_sqm) / 980.665

        # 驗證質量計算結果
        if not self._validate_mass_calculation(floor_mass, building_props, story):
            # 使用最小安全質量值
            floor_mass = max(floor_mass, self._get_minimum_safe_mass(building_props))

        return StoryParameters(
            story=story,
            mass=floor_mass,
            k=Ke,
            Fy=Fy,
            alpha=alpha,
            story_height=H,
            material_type=self._get_material_type(building_props.structural_system)
        )

    def generate_stick_model_parameters(self, building_props: BuildingProperties,
                                      building_id: str = None) -> StickModelParameters:
        """
        生成完整的Stick Model參數

        Args:
            building_props: 建築屬性
            building_id: 建築ID

        Returns:
            StickModelParameters: 完整的模型參數
        """
        if building_id is None:
            building_id = building_props.get_archetype_code()

        model = StickModelParameters(
            building_id=building_id,
            archetype_code=building_props.get_archetype_code()
        )

        # 為每一層生成參數
        for story in range(1, building_props.floor_count + 1):
            if building_props.structural_system == 'RC':
                story_params = self.calculate_rc_story_parameters(building_props, story)
            else:  # SC
                story_params = self.calculate_sc_story_parameters(building_props, story)

            model.stories.append(story_params)

        # 計算總高度和總質量
        model.total_height = sum(s.story_height for s in model.stories)
        model.total_mass = sum(s.mass for s in model.stories)

        logger.info(f"Generated Stick Model for {model.archetype_code}: "
                   f"{len(model.stories)} stories, {model.total_height:.0f}cm height, "
                   f"{model.total_mass:.1f} kgf·s²/cm mass")

        return model

    def _validate_mass_calculation(self, mass: float, building_props: BuildingProperties, story: int) -> bool:
        """
        驗證質量計算結果是否合理

        Args:
            mass: 計算得到的質量 (kgf·s²/cm)
            building_props: 建築屬性
            story: 樓層號

        Returns:
            bool: True if mass is valid
        """
        try:
            # 檢查基本數值有效性
            if mass <= 0 or np.isnan(mass) or np.isinf(mass):
                logger.error(f"Invalid mass value {mass} for story {story} of building area {building_props.representative_area_sqm}m² (representative)")
                return False

            # 檢查質量是否過小 (可能導致數值問題)
            min_mass = 1e-6  # 最小質量閾值
            if mass < min_mass:
                logger.warning(f"Very small mass {mass} for story {story}, may cause numerical issues")
                return False

            # 檢查質量是否合理 (基於建築面積的合理性檢查)
            expected_mass_range = self._get_expected_mass_range(building_props)
            if not (expected_mass_range[0] <= mass <= expected_mass_range[1]):
                logger.warning(f"Mass {mass:.6f} for story {story} is outside expected range "
                             f"[{expected_mass_range[0]:.6f}, {expected_mass_range[1]:.6f}] for area {building_props.representative_area_sqm}m² (representative)")
                # 不返回False，僅警告，允許使用但會調整

            logger.debug(f"Mass validation passed for story {story}: {mass:.6f} kgf·s²/cm")
            return True

        except Exception as e:
            logger.error(f"Mass validation error for story {story}: {e}")
            return False

    def _get_expected_mass_range(self, building_props: BuildingProperties) -> Tuple[float, float]:
        """
        獲取基於建築面積的預期質量範圍

        Args:
            building_props: 建築屬性

        Returns:
            Tuple[float, float]: (最小質量, 最大質量) in kgf·s²/cm
        """
        area_sqm = building_props.representative_area_sqm  # 使用代表性面積

        # 基於典型建築質量密度範圍
        min_density = 200  # kg/m² (輕量化建築)
        max_density = 1000  # kg/m² (重型建築)

        # 轉換為 kgf·s²/cm 單位
        min_mass = (min_density * area_sqm) / 980.665  # kgf·s²/cm
        max_mass = (max_density * area_sqm) / 980.665  # kgf·s²/cm

        return min_mass, max_mass

    def _get_minimum_safe_mass(self, building_props: BuildingProperties) -> float:
        """
        獲取最小安全質量值，避免數值問題

        Args:
            building_props: 建築屬性

        Returns:
            float: 最小安全質量 in kgf·s²/cm
        """
        # 基於建築面積的最小質量
        area_sqm = building_props.representative_area_sqm  # 使用代表性面積
        min_safe_density = 100  # kg/m² (非常保守的最小值)

        min_safe_mass = (min_safe_density * area_sqm) / 980.665

        # 確保不小於絕對最小值
        absolute_min = 1e-3  # kgf·s²/cm
        return max(min_safe_mass, absolute_min)


def test_archetype_generator():
    """測試原型參數生成器"""
    from building_classifier import BuildingProperties

    generator = ArchetypeParameterGenerator()

    # 測試樣本
    test_buildings = [
        BuildingProperties(
            floor_count=5,
            structural_system='RC',
            construction_era='PRE',
            area_scale='S',
            area_sqm=120.0,
            representative_area_sqm=100.0,  # S類標準面積
            height=17.5,
            age=30
        ),
        BuildingProperties(
            floor_count=12,
            structural_system='SC',
            construction_era='POST',
            area_scale='L',
            area_sqm=800.0,
            representative_area_sqm=700.0,  # L類標準面積
            height=42.0,
            age=15
        )
    ]

    print("Testing Archetype Parameter Generator...")
    for i, building in enumerate(test_buildings):
        print(f"\nBuilding {i+1}: {building.get_archetype_code()}")

        model = generator.generate_stick_model_parameters(building)

        print(f"Total Height: {model.total_height:.0f} cm")
        print(f"Total Mass: {model.total_mass:.2f} kgf·s²/cm")
        print("Story Parameters:")

        for story in model.stories:
            print(f"  Story {story.story}: "
                 f"K={story.k:.0f} kgf/cm, "
                 f"Fy={story.Fy:.0f} kgf, "
                 f"α={story.alpha:.3f}")


if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    # 執行測試
    test_archetype_generator()