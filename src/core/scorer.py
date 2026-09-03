# core/scorer.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import numpy as np
import tomllib

# ---------------------------------------------------------------------------
# Config TypedDicts
# ---------------------------------------------------------------------------

class ScorerConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float


class ScorerConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int


class ScorerConfigGrades(TypedDict):
    excellent: int
    good: int
    fair: int
    poor: int


class ScorerAppConfig(TypedDict):
    scoring: ScorerConfigScoring
    detection: ScorerConfigDetection
    grades: ScorerConfigGrades


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ScorerException(Exception):
    pass


class ConfigLoadError(ScorerException):
    pass


class ScoreCalculationError(ScorerException):
    pass


class EvaluationError(ScorerException):
    pass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoreLabel:
    category: str
    color_hex: str


@dataclass(frozen=True)
class QualityIssue:
    column: str
    metric: str
    severity: str
    score_impact: float
    description: str


@dataclass(frozen=True)
class DatasetSummary:
    overall_score: int
    label: ScoreLabel
    issues: list[QualityIssue]


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_scoring_config() -> ScorerAppConfig:
    try:
        config_path = Path(__file__).resolve().parents[2] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f)  # type: ignore
    except FileNotFoundError:
        return {
            "scoring": {
                "completeness_weight": 0.40,
                "uniqueness_weight":   0.20,
                "consistency_weight":  0.20,
                "outlier_weight":      0.20,
            },
            "detection": {
                "outlier_iqr_multiplier": 1.5,
                "max_upload_mb": 200,
            },
            "grades": {
                "excellent": 85,
                "good": 70,
                "fair": 50,
                "poor": 30,
            },
        }
    except tomllib.TOMLDecodeError as e:
        raise ConfigLoadError(f"Malformed TOML syntax inside configuration file: {e}")


_CONFIG: ScorerAppConfig = load_scoring_config()
_W_COMPLETENESS: float = _CONFIG["scoring"]["completeness_weight"]
_W_UNIQUENESS:   float = _CONFIG["scoring"]["uniqueness_weight"]
_W_CONSISTENCY:  float = _CONFIG["scoring"]["consistency_weight"]
_W_OUTLIER:      float = _CONFIG["scoring"]["outlier_weight"]

_GRADES = _CONFIG.get("grades", {"excellent": 85, "good": 70, "fair": 50, "poor": 30})


def _is_numeric_dtype(dtype_str: str) -> bool:
    dtype = dtype_str.lower()
    if "bool" in dtype:
        return False
    return any(t in dtype for t in ("int", "float", "decimal", "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64", "f32", "f64"))


def score_column(col_stats: dict[str, Any]) -> int:
    try:
        total_rows = int(col_stats.get("total_rows", 1))
        if total_rows <= 0:
            total_rows = 1

        dtype = str(col_stats.get("dtype", ""))
        missing_cnt = int(col_stats.get("missing_count", 0))
        unique_cnt = int(col_stats.get("unique_count", 0))
        outlier_cnt = int(col_stats.get("outlier_count", 0))
        mismatch_cnt = int(col_stats.get("mismatch_count", 0))

        # --- Completeness ------------------------------------------------
        missing_pct = (missing_cnt / total_rows) * 100.0
        completeness_score = max(0.0, 100.0 - missing_pct)

        # --- Uniqueness (context-aware) ----------------------------------
        uniqueness_ratio = unique_cnt / total_rows
        is_numeric = _is_numeric_dtype(dtype)

        if is_numeric:
            if uniqueness_ratio < 0.05:
                uniqueness_score = 20.0
            elif uniqueness_ratio < 0.20:
                uniqueness_score = 60.0
            else:
                uniqueness_score = 85.0
        else:
            if uniqueness_ratio > 0.95:
                uniqueness_score = 65.0
            elif uniqueness_ratio > 0.60:
                uniqueness_score = 80.0
            elif uniqueness_ratio > 0.05:
                uniqueness_score = 90.0
            elif uniqueness_ratio > 0.01:
                uniqueness_score = 60.0
            else:
                uniqueness_score = 20.0

        # --- Consistency (type mismatches) --------------------------------
        mismatch_pct = (mismatch_cnt / total_rows) * 100.0
        consistency_score = max(0.0, 100.0 - (mismatch_pct * 2.5))

        # --- Outlier rate  ------------------------------------------------
        if is_numeric:
            outlier_pct = (outlier_cnt / total_rows) * 100.0
            outlier_score = max(0.0, 100.0 - (outlier_pct * 3.0))

            raw_weighted = (
                (_W_COMPLETENESS * completeness_score) +
                (_W_UNIQUENESS   * uniqueness_score)   +
                (_W_CONSISTENCY  * consistency_score)  +
                (_W_OUTLIER      * outlier_score)
            )
        else:
            total_w = _W_COMPLETENESS + _W_UNIQUENESS + _W_CONSISTENCY
            if total_w == 0:
                total_w = 1.0
            w_c = _W_COMPLETENESS / total_w
            w_u = _W_UNIQUENESS   / total_w
            w_x = _W_CONSISTENCY  / total_w

            raw_weighted = (
                (w_c * completeness_score) +
                (w_u * uniqueness_score)   +
                (w_x * consistency_score)
            )

        return int(np.clip(np.round(raw_weighted), 0, 100))

    except Exception as e:
        raise ScoreCalculationError(f"Failed to calculate column quality score: {e}")


def score_dataframe(profile: dict[str, dict[str, Any]]) -> int:
    try:
        if not profile:
            return 0
        scores: list[int] = [score_column(stats) for stats in profile.values()]
        mean_score = float(np.mean(scores))

        # Apply duplicate penalty ONCE at the dataset level if dataset_duplicate_count is present
        first_col = next(iter(profile.values()))
        total_rows = int(first_col.get("total_rows", 1))
        if total_rows <= 0:
            total_rows = 1

        dup_cnt = int(first_col.get("dataset_duplicate_count", 0))
        dup_pct = (dup_cnt / total_rows) * 100.0
        dup_penalty = min(20.0, dup_pct * 0.5)

        final_score = max(0.0, mean_score - dup_penalty)
        return int(np.clip(np.round(final_score), 0, 100))
    except Exception as e:
        raise ScoreCalculationError(f"Failed to compute dataset level quality score: {e}")


def get_score_label(score: int) -> ScoreLabel:
    try:
        if score >= _GRADES.get("excellent", 85):
            return ScoreLabel(category="Excellent", color_hex="#2ECC71")
        if score >= _GRADES.get("good", 70):
            return ScoreLabel(category="Good",      color_hex="#3498DB")
        if score >= _GRADES.get("fair", 50):
            return ScoreLabel(category="Fair",      color_hex="#F1C40F")
        if score >= _GRADES.get("poor", 30):
            return ScoreLabel(category="Poor",      color_hex="#E67E22")
        return ScoreLabel(category="Critical",      color_hex="#E74C3C")
    except Exception as e:
        raise EvaluationError(f"Failed to evaluate score label: {e}")


def generate_issue_summary(profile: dict[str, dict[str, Any]]) -> list[QualityIssue]:
    try:
        issues_list: list[QualityIssue] = []

        if not profile:
            return issues_list

        first_col = next(iter(profile.values()))
        total_rows = int(first_col.get("total_rows", 1))
        if total_rows <= 0:
            total_rows = 1

        # Check dataset-level duplicates once
        dataset_dup_cnt = int(first_col.get("dataset_duplicate_count", 0))
        if dataset_dup_cnt > 0:
            duplicate_pct = (dataset_dup_cnt / total_rows) * 100.0
            penalty = min(20.0, duplicate_pct * 0.5)
            severity = "High" if duplicate_pct > 5.0 else "Medium"
            issues_list.append(QualityIssue(
                column="Dataset",
                metric="Duplicates",
                severity=severity,
                score_impact=float(np.round(penalty, 2)),
                description=f"Dataset contains {dataset_dup_cnt} duplicate rows ({duplicate_pct:.2f}% of total).",
            ))

        total_w = _W_COMPLETENESS + _W_UNIQUENESS + _W_CONSISTENCY
        if total_w == 0:
            total_w = 1.0

        w_completeness_non_numeric = _W_COMPLETENESS / total_w
        w_consistency_non_numeric = _W_CONSISTENCY / total_w

        for col_name, stats in profile.items():
            dtype = str(stats.get("dtype", ""))
            is_numeric = _is_numeric_dtype(dtype)

            missing_pct = float(stats.get("missing_percentage", 0.0))
            if missing_pct > 0.0:
                comp_w = _W_COMPLETENESS if is_numeric else w_completeness_non_numeric
                impact = missing_pct * comp_w
                severity = (
                    "Critical" if missing_pct > 30.0
                    else "High" if missing_pct > 10.0
                    else "Medium"
                )
                issues_list.append(QualityIssue(
                    column=col_name,
                    metric="Completeness",
                    severity=severity,
                    score_impact=float(np.round(impact, 2)),
                    description=f"Column contains {missing_pct:.2f}% missing values.",
                ))

            mismatch_cnt = int(stats.get("mismatch_count", 0))
            if mismatch_cnt > 0:
                mismatch_pct = (mismatch_cnt / total_rows) * 100.0
                cons_w = _W_CONSISTENCY if is_numeric else w_consistency_non_numeric
                impact = mismatch_pct * cons_w
                severity = "High" if mismatch_pct > 15.0 else "Medium"
                issues_list.append(QualityIssue(
                    column=col_name,
                    metric="Type Consistency",
                    severity=severity,
                    score_impact=float(np.round(impact, 2)),
                    description=f"Detected {mismatch_cnt} structural type anomalies in column values.",
                ))

            outlier_cnt = int(stats.get("outlier_count", 0))
            if outlier_cnt > 0 and is_numeric:
                outlier_pct = (outlier_cnt / total_rows) * 100.0
                impact = outlier_pct * _W_OUTLIER
                severity = "High" if outlier_pct > 10.0 else "Medium"
                issues_list.append(QualityIssue(
                    column=col_name,
                    metric="Outlier Rate",
                    severity=severity,
                    score_impact=float(np.round(impact, 2)),
                    description=f"Detected {outlier_cnt} statistical anomalies outside IQR thresholds.",
                ))

        severity_map = {"Critical": 0, "High": 1, "Medium": 2}
        return sorted(
            issues_list,
            key=lambda x: (severity_map.get(x.severity, 3), -x.score_impact),
        )

    except Exception as e:
        raise EvaluationError(f"Failed to generate issue summary: {e}")


def generate_dataset_summary(
    profile: dict[str, dict[str, Any]]
) -> DatasetSummary:
    try:
        overall_score = score_dataframe(profile)
        label = get_score_label(overall_score)
        issues = generate_issue_summary(profile)
        return DatasetSummary(
            overall_score=overall_score,
            label=label,
            issues=issues,
        )
    except Exception as e:
        raise ScoreCalculationError(f"Unexpected failure compiling dataset summary: {e}")
