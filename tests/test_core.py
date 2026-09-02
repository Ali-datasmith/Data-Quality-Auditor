import pandas as pd
import polars as pl
import pytest

from core.profiler import (
    detect_duplicates,
    detect_outliers,
    generate_profile,
    run_duckdb_anomalies,
)
from core.scorer import (
    get_score_label,
    score_column,
    score_dataframe,
)
from credentials import get_user_name, validate_credentials
from utils.cleaner import (
    apply_fixes,
    apply_fixes_lazy,
    generate_change_log,
)

# ============================================================================
# Auth Tests
# ============================================================================

def test_auth_valid_credentials() -> None:
    is_valid, msg = validate_credentials("Ali-datasmith", "Qx9#mK2$vL7@nR4!")
    assert is_valid is True
    assert "Welcome back" in msg


def test_auth_invalid_credentials() -> None:
    is_valid, msg = validate_credentials("Ali-datasmith", "WrongPassword")
    assert is_valid is False
    assert "Invalid credentials" in msg


def test_auth_missing_credentials() -> None:
    is_valid, msg = validate_credentials("", "")
    assert is_valid is False
    assert "Username and password required" in msg


def test_get_user_name() -> None:
    assert get_user_name("Ali-datasmith") == "Ali Datasmith"
    assert get_user_name("UnknownUser") == "UnknownUser"


# ============================================================================
# Profiler & Polars Lazy Tests
# ============================================================================

@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "num_col": [10.0, 12.0, 11.0, 100.0, None, 10.0],
        "str_col": ["alpha", "beta", "gamma", "alpha", "beta", "alpha"],
        "bool_col": [True, False, True, True, False, True],
    })


def test_generate_profile_lazy(sample_df: pd.DataFrame) -> None:
    profile = generate_profile(sample_df)
    assert "num_col" in profile
    assert "str_col" in profile

    num_p = profile["num_col"]
    assert num_p.missing_count == 1
    assert num_p.unique_count == 5  # 10.0, 12.0, 11.0, 100.0, Null


def test_detect_duplicates_lazy(sample_df: pd.DataFrame) -> None:
    # Row 0 and Row 5 are identical: (10.0, 'alpha', True)
    dup_report = detect_duplicates(sample_df)
    assert dup_report.count == 1
    assert 5 in dup_report.indices


def test_detect_outliers_lazy(sample_df: pd.DataFrame) -> None:
    outlier_report = detect_outliers(sample_df, "num_col")
    assert outlier_report.count == 1
    assert 3 in outlier_report.indices  # value 100.0 at index 3


def test_detect_outliers_boolean_column(sample_df: pd.DataFrame) -> None:
    outlier_report = detect_outliers(sample_df, "bool_col")
    assert outlier_report.count == 0
    assert outlier_report.lower_fence == 0.0


def test_run_duckdb_anomalies(sample_df: pd.DataFrame) -> None:
    report = run_duckdb_anomalies(sample_df)
    assert isinstance(report.null_columns, list)
    assert isinstance(report.type_mismatches, list)


# ============================================================================
# Scorer & Math Calculation Tests
# ============================================================================

def test_score_column_numeric() -> None:
    col_stats = {
        "total_rows": 100,
        "dtype": "float64",
        "missing_count": 5,
        "unique_count": 50,
        "outlier_count": 2,
        "mismatch_count": 0,
        "duplicate_count": 0,
    }
    score = score_column(col_stats)
    assert 0 <= score <= 100
    assert score > 70


def test_score_column_string_no_outlier_penalty() -> None:
    col_stats = {
        "total_rows": 100,
        "dtype": "Utf8",
        "missing_count": 0,
        "unique_count": 20,
        "outlier_count": 0,
        "mismatch_count": 0,
        "duplicate_count": 0,
    }
    score = score_column(col_stats)
    assert score >= 85


def test_score_dataframe(sample_df: pd.DataFrame) -> None:
    profile = generate_profile(sample_df)
    col_stats_dict = {}
    for col, p in profile.items():
        col_stats_dict[col] = {
            "total_rows": len(sample_df),
            "dtype": p.dtype,
            "missing_count": p.missing_count,
            "unique_count": p.unique_count,
            "outlier_count": 0,
            "mismatch_count": 0,
            "duplicate_count": 0,
        }
    overall = score_dataframe(col_stats_dict)
    assert 0 <= overall <= 100


def test_get_score_label() -> None:
    label_90 = get_score_label(90)
    assert label_90.category == "Excellent"
    label_20 = get_score_label(20)
    assert label_20.category == "Critical"


# ============================================================================
# Cleaner & Transformation Tests
# ============================================================================

def test_apply_fixes_lazy() -> None:
    lf = pl.LazyFrame({
        "num": [1.0, None, 100.0],
        "cat": ["a", "b", "a"],
    })

    fixes: list[dict[str, object]] = [
        {
            "column": "num",
            "action_type": "FILL_MISSING",
        },
        {
            "column": "num",
            "action_type": "CAP_OUTLIERS",
            "details": {"lower_fence": 0.0, "upper_fence": 50.0},
        },
    ]

    cleaned_lf = apply_fixes_lazy(lf, fixes)  # type: ignore[arg-type]
    cleaned_df = cleaned_lf.collect()

    assert cleaned_df["num"].null_count() == 0
    max_val = float(cleaned_df["num"].max())  # type: ignore[arg-type]
    assert max_val <= 50.0


def test_generate_change_log(sample_df: pd.DataFrame) -> None:
    cleaned = apply_fixes(sample_df, [{"action_type": "DROP_DUPLICATES"}])
    log = generate_change_log(sample_df, cleaned)
    assert isinstance(log.rows_dropped, int)
    assert isinstance(log.mutations_applied, dict)
