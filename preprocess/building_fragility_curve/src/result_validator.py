#!/usr/bin/env python3
"""
Result Validation and Quality Assurance Module

此模組負責易損性分析結果的驗證和品質保證，確保輸出資料的正確性和可靠性。

主要功能：
1. 易損性曲線結果驗證
2. 建築分類一致性檢查
3. 數值範圍和邏輯合理性驗證
4. 統計品質指標計算
5. 詳細驗證報告生成
"""

import os
import sys
import time
import logging
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
import statistics

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from building_classifier import BuildingProperties
from fragility_cache import FragilityCurveResult
from utils.pga_mapping import PGAIntensityMapper

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """驗證結果"""
    item_id: str
    check_name: str
    passed: bool
    severity: str  # 'error', 'warning', 'info'
    message: str
    details: Optional[Dict] = None


@dataclass
class QualityMetrics:
    """品質指標"""
    total_items: int
    valid_items: int
    error_count: int
    warning_count: int
    quality_score: float
    completeness_rate: float


class FragilityCurveValidator:
    """
    易損性曲線驗證器

    驗證易損性曲線結果的正確性和合理性
    """

    def __init__(self):
        """初始化驗證器"""
        self.pga_mapper = PGAIntensityMapper()
        self.validation_rules = self._initialize_validation_rules()
        self.validation_results: List[ValidationResult] = []

    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """初始化驗證規則"""
        return {
            'probability_range': {
                'min': 0.0,
                'max': 1.0,
                'description': 'Probabilities must be between 0 and 1'
            },
            'monotonicity_tolerance': {
                'max_decrease': 0.05,  # 允許5%的下降
                'description': 'Fragility curves should be monotonically increasing'
            },
            'reasonable_probability_levels': {
                'level_3_max': 0.01,   # 3級地震倒塌機率應低於1%
                'level_4_max': 0.05,   # 4級地震倒塌機率應低於5%
                'level_7_min': 0.1,    # 7級地震倒塌機率應高於10%
                'description': 'Probabilities should be reasonable for each intensity level'
            },
            'required_intensity_levels': {
                'levels': ['3', '4', '5弱', '5強', '6弱', '6強', '7'],
                'description': 'All required intensity levels must be present'
            }
        }

    def validate_fragility_curve(self,
                                item_id: str,
                                fragility_curve: Dict[str, float]) -> List[ValidationResult]:
        """
        驗證單一易損性曲線

        Args:
            item_id: 項目ID
            fragility_curve: 易損性曲線字典

        Returns:
            List[ValidationResult]: 驗證結果列表
        """
        results = []

        # 檢查1: 必要強度級別完整性
        required_levels = self.validation_rules['required_intensity_levels']['levels']
        missing_levels = [level for level in required_levels if level not in fragility_curve]

        if missing_levels:
            results.append(ValidationResult(
                item_id=item_id,
                check_name="completeness",
                passed=False,
                severity="error",
                message=f"Missing intensity levels: {missing_levels}",
                details={'missing_levels': missing_levels}
            ))
        else:
            results.append(ValidationResult(
                item_id=item_id,
                check_name="completeness",
                passed=True,
                severity="info",
                message="All required intensity levels present"
            ))

        # 檢查2: 機率值範圍
        prob_range = self.validation_rules['probability_range']
        invalid_probs = {}

        for level, prob in fragility_curve.items():
            if not isinstance(prob, (int, float)):
                invalid_probs[level] = f"Not numeric: {type(prob)}"
            elif not (prob_range['min'] <= prob <= prob_range['max']):
                invalid_probs[level] = f"Out of range: {prob}"
            elif np.isnan(prob) or np.isinf(prob):
                invalid_probs[level] = f"Invalid value: {prob}"

        if invalid_probs:
            results.append(ValidationResult(
                item_id=item_id,
                check_name="probability_range",
                passed=False,
                severity="error",
                message=f"Invalid probability values: {invalid_probs}",
                details={'invalid_probabilities': invalid_probs}
            ))
        else:
            results.append(ValidationResult(
                item_id=item_id,
                check_name="probability_range",
                passed=True,
                severity="info",
                message="All probability values are in valid range"
            ))

        # 檢查3: 單調性
        if all(level in fragility_curve for level in required_levels):
            ordered_probs = [fragility_curve[level] for level in required_levels]
            monotonicity_violations = []

            for i in range(1, len(ordered_probs)):
                decrease = ordered_probs[i-1] - ordered_probs[i]
                if decrease > self.validation_rules['monotonicity_tolerance']['max_decrease']:
                    monotonicity_violations.append({
                        'from_level': required_levels[i-1],
                        'to_level': required_levels[i],
                        'decrease': decrease
                    })

            if monotonicity_violations:
                results.append(ValidationResult(
                    item_id=item_id,
                    check_name="monotonicity",
                    passed=False,
                    severity="warning",
                    message=f"Monotonicity violations detected: {len(monotonicity_violations)}",
                    details={'violations': monotonicity_violations}
                ))
            else:
                results.append(ValidationResult(
                    item_id=item_id,
                    check_name="monotonicity",
                    passed=True,
                    severity="info",
                    message="Fragility curve is properly monotonic"
                ))

        # 檢查4: 合理性檢查
        reasonable_levels = self.validation_rules['reasonable_probability_levels']
        reasonableness_issues = []

        if '3' in fragility_curve and fragility_curve['3'] > reasonable_levels['level_3_max']:
            reasonableness_issues.append(f"Level 3 probability too high: {fragility_curve['3']:.4f}")

        if '4' in fragility_curve and fragility_curve['4'] > reasonable_levels['level_4_max']:
            reasonableness_issues.append(f"Level 4 probability too high: {fragility_curve['4']:.4f}")

        if '7' in fragility_curve and fragility_curve['7'] < reasonable_levels['level_7_min']:
            reasonableness_issues.append(f"Level 7 probability too low: {fragility_curve['7']:.4f}")

        if reasonableness_issues:
            results.append(ValidationResult(
                item_id=item_id,
                check_name="reasonableness",
                passed=False,
                severity="warning",
                message=f"Reasonableness issues: {reasonableness_issues}",
                details={'issues': reasonableness_issues}
            ))
        else:
            results.append(ValidationResult(
                item_id=item_id,
                check_name="reasonableness",
                passed=True,
                severity="info",
                message="Probability levels appear reasonable"
            ))

        return results

    def validate_batch_results(self,
                             results: Dict[str, Optional[FragilityCurveResult]]) -> QualityMetrics:
        """
        批量驗證結果

        Args:
            results: 批量分析結果

        Returns:
            QualityMetrics: 品質指標
        """
        logger.info(f"Starting batch validation of {len(results)} results")

        all_validation_results = []
        valid_items = 0
        error_count = 0
        warning_count = 0

        for item_id, result in results.items():
            if result is None:
                # 分析失敗的情況
                all_validation_results.append(ValidationResult(
                    item_id=item_id,
                    check_name="analysis_success",
                    passed=False,
                    severity="error",
                    message="Analysis failed - no result available"
                ))
                error_count += 1
            else:
                # 驗證成功的結果
                curve_results = self.validate_fragility_curve(
                    item_id, result.collapse_probabilities
                )
                all_validation_results.extend(curve_results)

                # 統計驗證結果
                has_errors = any(r.severity == "error" and not r.passed for r in curve_results)
                has_warnings = any(r.severity == "warning" and not r.passed for r in curve_results)

                if not has_errors:
                    valid_items += 1

                if has_errors:
                    error_count += 1
                elif has_warnings:
                    warning_count += 1

        # 儲存驗證結果
        self.validation_results = all_validation_results

        # 計算品質指標
        total_items = len(results)
        completeness_rate = sum(1 for r in results.values() if r is not None) / total_items if total_items > 0 else 0
        quality_score = valid_items / total_items if total_items > 0 else 0

        metrics = QualityMetrics(
            total_items=total_items,
            valid_items=valid_items,
            error_count=error_count,
            warning_count=warning_count,
            quality_score=quality_score,
            completeness_rate=completeness_rate
        )

        logger.info(f"Batch validation complete:")
        logger.info(f"  Total items: {total_items}")
        logger.info(f"  Valid items: {valid_items}")
        logger.info(f"  Quality score: {quality_score:.2%}")
        logger.info(f"  Completeness: {completeness_rate:.2%}")

        return metrics

    def generate_validation_report(self,
                                 metrics: QualityMetrics,
                                 output_file: str) -> None:
        """
        生成驗證報告

        Args:
            metrics: 品質指標
            output_file: 輸出檔案路徑
        """
        try:
            # 統計各類驗證結果
            check_summary = {}
            severity_summary = {'error': 0, 'warning': 0, 'info': 0}

            for result in self.validation_results:
                # 按檢查類型統計
                if result.check_name not in check_summary:
                    check_summary[result.check_name] = {'passed': 0, 'failed': 0}

                if result.passed:
                    check_summary[result.check_name]['passed'] += 1
                else:
                    check_summary[result.check_name]['failed'] += 1

                # 按嚴重程度統計
                severity_summary[result.severity] += 1

            # 建立報告
            report = {
                'validation_summary': {
                    'timestamp': datetime.now().isoformat(),
                    'total_items': metrics.total_items,
                    'valid_items': metrics.valid_items,
                    'error_count': metrics.error_count,
                    'warning_count': metrics.warning_count,
                    'quality_score': metrics.quality_score,
                    'completeness_rate': metrics.completeness_rate
                },
                'check_summary': check_summary,
                'severity_summary': severity_summary,
                'validation_rules': self.validation_rules,
                'detailed_results': []
            }

            # 添加詳細結果（只包含失敗的檢查）
            failed_results = [r for r in self.validation_results if not r.passed]
            for result in failed_results:
                report['detailed_results'].append({
                    'item_id': result.item_id,
                    'check_name': result.check_name,
                    'severity': result.severity,
                    'message': result.message,
                    'details': result.details
                })

            # 寫入檔案
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"Validation report saved: {output_file}")

        except Exception as e:
            logger.error(f"Failed to generate validation report: {e}")

    def get_validation_statistics(self) -> Dict[str, Any]:
        """獲取驗證統計資訊"""
        if not self.validation_results:
            return {}

        # 按檢查類型統計
        check_stats = {}
        for result in self.validation_results:
            if result.check_name not in check_stats:
                check_stats[result.check_name] = {'total': 0, 'passed': 0, 'failed': 0}

            check_stats[result.check_name]['total'] += 1
            if result.passed:
                check_stats[result.check_name]['passed'] += 1
            else:
                check_stats[result.check_name]['failed'] += 1

        # 計算通過率
        for check_name in check_stats:
            stats = check_stats[check_name]
            stats['pass_rate'] = stats['passed'] / stats['total'] if stats['total'] > 0 else 0

        return {
            'total_validations': len(self.validation_results),
            'check_statistics': check_stats,
            'overall_pass_rate': sum(1 for r in self.validation_results if r.passed) / len(self.validation_results)
        }


class ArchetypeConsistencyValidator:
    """
    建築原型一致性驗證器

    驗證建築分類和參數的一致性
    """

    def __init__(self):
        """初始化一致性驗證器"""
        self.consistency_issues = []

    def validate_archetype_consistency(self,
                                     building_id: str,
                                     building_props: BuildingProperties,
                                     fragility_result: FragilityCurveResult) -> List[ValidationResult]:
        """
        驗證建築原型一致性

        Args:
            building_id: 建築ID
            building_props: 建築屬性
            fragility_result: 易損性結果

        Returns:
            List[ValidationResult]: 驗證結果
        """
        results = []

        # 檢查原型編碼一致性
        expected_code = building_props.get_archetype_code()
        actual_code = fragility_result.archetype_code

        if expected_code != actual_code:
            results.append(ValidationResult(
                item_id=building_id,
                check_name="archetype_code_consistency",
                passed=False,
                severity="error",
                message=f"Archetype code mismatch: expected {expected_code}, got {actual_code}",
                details={
                    'expected_code': expected_code,
                    'actual_code': actual_code
                }
            ))
        else:
            results.append(ValidationResult(
                item_id=building_id,
                check_name="archetype_code_consistency",
                passed=True,
                severity="info",
                message="Archetype code is consistent"
            ))

        # 檢查時間戳有效性
        try:
            timestamp = datetime.fromisoformat(fragility_result.computed_timestamp)
            if timestamp > datetime.now():
                results.append(ValidationResult(
                    item_id=building_id,
                    check_name="timestamp_validity",
                    passed=False,
                    severity="warning",
                    message="Computation timestamp is in the future"
                ))
            else:
                results.append(ValidationResult(
                    item_id=building_id,
                    check_name="timestamp_validity",
                    passed=True,
                    severity="info",
                    message="Timestamp is valid"
                ))
        except Exception as e:
            results.append(ValidationResult(
                item_id=building_id,
                check_name="timestamp_validity",
                passed=False,
                severity="error",
                message=f"Invalid timestamp format: {e}"
            ))

        # 檢查計算時間合理性
        computation_time = fragility_result.computation_time
        if computation_time < 0:
            results.append(ValidationResult(
                item_id=building_id,
                check_name="computation_time_validity",
                passed=False,
                severity="error",
                message=f"Negative computation time: {computation_time}"
            ))
        elif computation_time > 7200:  # 2小時
            results.append(ValidationResult(
                item_id=building_id,
                check_name="computation_time_validity",
                passed=False,
                severity="warning",
                message=f"Very long computation time: {computation_time:.1f}s"
            ))
        else:
            results.append(ValidationResult(
                item_id=building_id,
                check_name="computation_time_validity",
                passed=True,
                severity="info",
                message="Computation time is reasonable"
            ))

        return results


def test_validators():
    """測試驗證器"""
    from building_classifier import BuildingProperties
    from fragility_cache import FragilityCurveResult
    from datetime import datetime

    print("Testing Result Validators...")

    # 建立測試資料
    # 好的易損性曲線
    good_curve = {
        '3': 0.001,
        '4': 0.005,
        '5弱': 0.02,
        '5強': 0.05,
        '6弱': 0.15,
        '6強': 0.35,
        '7': 0.65
    }

    # 有問題的易損性曲線
    bad_curve = {
        '3': 0.1,    # 太高
        '4': 0.08,   # 非單調
        '5弱': 1.2,  # 超出範圍
        '6弱': 0.2,  # 缺少級別
        '7': 0.05    # 太低
    }

    # 測試易損性曲線驗證器
    fragility_validator = FragilityCurveValidator()

    print("\nTesting good fragility curve:")
    good_results = fragility_validator.validate_fragility_curve("good_test", good_curve)
    for result in good_results:
        print(f"  {result.check_name}: {'PASS' if result.passed else 'FAIL'} - {result.message}")

    print("\nTesting bad fragility curve:")
    bad_results = fragility_validator.validate_fragility_curve("bad_test", bad_curve)
    for result in bad_results:
        print(f"  {result.check_name}: {'PASS' if result.passed else 'FAIL'} - {result.message}")

    # 測試批量驗證
    test_results = {
        'building_001': FragilityCurveResult(
            archetype_code="RC-PRE-5F-S",
            collapse_probabilities=good_curve,
            analysis_metadata={},
            computed_timestamp=datetime.now().isoformat(),
            computation_time=120.0
        ),
        'building_002': FragilityCurveResult(
            archetype_code="RC-POST-8F-M",
            collapse_probabilities=bad_curve,
            analysis_metadata={},
            computed_timestamp=datetime.now().isoformat(),
            computation_time=180.0
        ),
        'building_003': None  # 分析失敗
    }

    print("\nTesting batch validation:")
    metrics = fragility_validator.validate_batch_results(test_results)
    print(f"Quality Score: {metrics.quality_score:.2%}")
    print(f"Completeness: {metrics.completeness_rate:.2%}")
    print(f"Errors: {metrics.error_count}")
    print(f"Warnings: {metrics.warning_count}")

    print("Validation tests completed!")


if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    # 執行測試
    test_validators()