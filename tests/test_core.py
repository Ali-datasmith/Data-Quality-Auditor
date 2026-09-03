import pandas as pd
import polars as pl
import pytest

from app import _build_enriched_profile
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
# Edge Cases & Audit Tests
# ============================================================================

def test_empty_dataframe_profiling() -> None:
    empty_df = pd.DataFrame(columns=["a", "b"])
    profile = generate_profile(empty_df)
    assert "a" in profile
    assert profile["a"].missing_count == 0
    assert profile["a"].missing_percentage == 0.0

    enriched = _build_enriched_profile(empty_df)
    assert score_dataframe(enriched) == 80


def test_all_null_dataframe_profiling() -> None:
    null_df = pd.DataFrame({"col_null": [None, None, None]})
    profile = generate_profile(null_df)
    assert profile["col_null"].missing_count == 3
    assert profile["col_null"].missing_percentage == 100.0


def test_iqr_outlier_calculation_bounds() -> None:
    # Distribution with known q25=3.0, q75=8.0, iqr=5.0
    # lower_fence = 3 - 1.5*5 = -4.5, upper_fence = 8 + 1.5*5 = 15.5
    df = pd.DataFrame({"vals": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 100.0]})
    report = detect_outliers(df, "vals")
    assert report.count == 1
    assert report.upper_fence == 15.5
    assert report.lower_fence == -4.5
    assert 9 in report.indices


# ============================================================================
# Regression Tests from Refactoring Protocol
# ============================================================================

def test_change_log_counts_filled_values_once() -> None:
    active_df = pd.DataFrame({"col1": [1.0, None, 3.0], "col2": ["a", "b", None]})
    cleaned_df = pd.DataFrame({"col1": [1.0, 2.0, 3.0], "col2": ["a", "b", "Unknown"]})
    log = generate_change_log(active_df, cleaned_df)
    assert log.mutations_applied["col1"] == 1
    assert log.mutations_applied["col2"] == 1


def test_apply_fixes_lazy_boolean_fill_is_type_safe() -> None:
    lf = pl.LazyFrame({"bool_col": [True, None, False]})
    fixes = [{"column": "bool_col", "action_type": "FILL_MISSING"}]
    cleaned_lf = apply_fixes_lazy(lf, fixes)
    res = cleaned_lf.collect()
    assert res["bool_col"].dtype == pl.Boolean
    assert res["bool_col"].null_count() == 0
    assert res["bool_col"].to_list() == [True, False, False]


def test_duplicate_penalty_applied_once_at_dataset_level() -> None:
    profile = {
        "col1": {
            "dtype": "Float64",
            "missing_count": 0,
            "unique_count": 10,
            "outlier_count": 0,
            "mismatch_count": 0,
            "total_rows": 10,
            "dataset_duplicate_count": 2,  # 20% duplicates -> penalty = min(20, 20*0.5) = 10 points
        },
        "col2": {
            "dtype": "Float64",
            "missing_count": 0,
            "unique_count": 10,
            "outlier_count": 0,
            "mismatch_count": 0,
            "total_rows": 10,
            "dataset_duplicate_count": 2,
        },
    }
        # Column scores without duplicate penalty = 97
    score1 = score_column(profile["col1"])
    score2 = score_column(profile["col2"])
    assert score1 == 97
    assert score2 == 97
    # Dataset score applying penalty ONCE = 97 - 10 = 87
    overall = score_dataframe(profile)
    assert overall == 87


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
    # Null values are excluded from unique_count: 10.0, 12.0, 11.0, 100.0 = 4
    assert num_p.unique_count == 4


def test_detect_duplicates_lazy(sample_df: pd.DataFrame) -> None:
    dup_report = detect_duplicates(sample_df)
    assert dup_report.count == 1
    assert 5 in dup_report.indices


def test_detect_outliers_lazy(sample_df: pd.DataFrame) -> None:
    outlier_report = detect_outliers(sample_df, "num_col")
    assert outlier_report.count == 1
    assert 3 in outlier_report.indices


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
    enriched = _build_enriched_profile(sample_df)
    overall = score_dataframe(enriched)
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
