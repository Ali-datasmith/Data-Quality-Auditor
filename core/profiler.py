# core/profiler.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, TypedDict, Union
import tomllib
import numpy as np
import pandas as pd
import polars as pl
import duckdb


class ConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float


class ConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int


class AppConfig(TypedDict):
    scoring: ConfigScoring
    detection: ConfigDetection


class ProfilerError(Exception):
    pass


class FileLoadError(ProfilerError):
    pass


class ProfileGenerationError(ProfilerError):
    pass


class DuplicateDetectionError(ProfilerError):
    pass


class OutlierDetectionError(ProfilerError):
    pass


class AnomalyDetectionError(ProfilerError):
    pass


@dataclass(frozen=True)
class ColumnProfile:
    dtype: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    min_value: Any
    max_value: Any
    mean_value: Union[float, None]
    std_value: Union[float, None]
    top_values: List[Dict[str, Any]]


@dataclass(frozen=True)
class DuplicateReport:
    count: int
    indices: List[int]


@dataclass(frozen=True)
class OutlierReport:
    count: int
    indices: List[int]
    lower_fence: float
    upper_fence: float


@dataclass(frozen=True)
class AnomalyReport:
    null_columns: List[str]
    all_zero_columns: List[str]
    type_mismatches: List[Dict[str, Any]]


def load_config() -> AppConfig:
    try:
        config_path = Path(__file__).resolve().parents[1] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f)  # type: ignore
    except FileNotFoundError:
        return {
            "scoring": {
                "completeness_weight": 0.3,
                "uniqueness_weight": 0.2,
                "consistency_weight": 0.3,
                "outlier_weight": 0.2
            },
            "detection": {
                "outlier_iqr_multiplier": 1.5,
                "max_upload_mb": 200
            }
        }
    except tomllib.TOMLDecodeError as e:
        raise ProfilerError(f"Invalid TOML in configuration file: {e}")


_CONFIG: AppConfig = load_config()
_IQR_MULTIPLIER: float = _CONFIG["detection"]["outlier_iqr_multiplier"]


def load_file(path: Path) -> pd.DataFrame:
    try:
        lf = pl.scan_csv(path, infer_schema_length=10000, try_parse_dates=True)
        df_pl = lf.collect()
        return df_pl.to_pandas()
    except pl.exceptions.ComputeError as e:
        raise FileLoadError(f"Polars failed to parse or scan the CSV: {e}")
    except FileNotFoundError as e:
        raise FileLoadError(f"Target CSV file not found at path: {e}")
    except Exception as e:
        raise FileLoadError(f"Unexpected error loading file: {e}")


def generate_profile(df: pd.DataFrame) -> Dict[str, ColumnProfile]:
    try:
        profile_results: Dict[str, ColumnProfile] = {}
        total_rows = len(df)

        for column in df.columns:
            col_series = df[column]
            missing_cnt = int(col_series.isna().sum())
            missing_pct = float((missing_cnt / total_rows) * 100) if total_rows > 0 else 0.0

            try:
                unique_cnt = int(col_series.nunique(dropna=True))
            except Exception:
                unique_cnt = int(col_series.astype(str).nunique())

            try:
                top_vc = col_series.value_counts(dropna=True).head(5)
                top_vals = [{"value": str(k), "count": int(v)} for k, v in top_vc.items()]
            except Exception:
                top_vals = []

            if pd.api.types.is_numeric_dtype(col_series):
                valid_num = col_series.dropna()
                min_v = float(valid_num.min()) if not valid_num.empty else None
                max_v = float(valid_num.max()) if not valid_num.empty else None
                mean_v = float(valid_num.mean()) if not valid_num.empty else None
                std_v = float(valid_num.std()) if not valid_num.empty and len(valid_num) > 1 else None
            elif pd.api.types.is_datetime64_any_dtype(col_series):
                min_v = str(col_series.min()) if col_series.notna().any() else None
                max_v = str(col_series.max()) if col_series.notna().any() else None
                mean_v = None
                std_v = None
            else:
                valid_str = col_series.dropna().astype(str)
                min_v = str(valid_str.min()) if not valid_str.empty else None
                max_v = str(valid_str.max()) if not valid_str.empty else None
                mean_v = None
                std_v = None

            profile_results[str(column)] = ColumnProfile(
                dtype=str(col_series.dtype),
                missing_count=missing_cnt,
                missing_percentage=missing_pct,
                unique_count=unique_cnt,
                min_value=min_v,
                max_value=max_v,
                mean_value=mean_v,
                std_value=std_v,
                top_values=top_vals
            )
        return profile_results
    except KeyError as e:
        raise ProfileGenerationError(f"Column axis mapping failed: {e}")
    except TypeError as e:
        raise ProfileGenerationError(f"Type error during stats aggregation: {e}")
    except Exception as e:
        raise ProfileGenerationError(f"Failed to generate dataframe profile: {e}")


def detect_duplicates(df: pd.DataFrame) -> DuplicateReport:
    try:
        duplicate_mask = df.duplicated(keep="first")
        duplicate_indices = df.index[duplicate_mask].tolist()
        return DuplicateReport(
            count=int(duplicate_mask.sum()),
            indices=[int(idx) for idx in duplicate_indices]
        )
    except ValueError as e:
        raise DuplicateDetectionError(f"Dataframe structure error in duplication check: {e}")
    except Exception as e:
        raise DuplicateDetectionError(f"Failed to detect duplicate rows: {e}")


def detect_outliers(df: pd.DataFrame, column: str) -> OutlierReport:
    try:
        col_series = df[column]

        # Exclude non-numeric AND boolean columns — booleans pass is_numeric_dtype
        # but numpy arithmetic (subtraction) fails on them
        if not pd.api.types.is_numeric_dtype(col_series) or pd.api.types.is_bool_dtype(col_series):
            return OutlierReport(count=0, indices=[], lower_fence=0.0, upper_fence=0.0)

        clean_series = col_series.dropna()
        if clean_series.empty:
            return OutlierReport(count=0, indices=[], lower_fence=0.0, upper_fence=0.0)

        q25, q75 = np.percentile(clean_series, [25, 75])
        iqr = q75 - q25

        lower_fence = float(q25 - (_IQR_MULTIPLIER * iqr))
        upper_fence = float(q75 + (_IQR_MULTIPLIER * iqr))

        outlier_mask = (col_series < lower_fence) | (col_series > upper_fence)
        outlier_indices = df.index[outlier_mask].tolist()

        return OutlierReport(
            count=int(outlier_mask.sum()),
            indices=[int(idx) for idx in outlier_indices],
            lower_fence=lower_fence,
            upper_fence=upper_fence
        )
    except KeyError as e:
        raise OutlierDetectionError(f"Target column '{column}' not found for outlier analysis: {e}")
    except TypeError as e:
        raise OutlierDetectionError(f"Non-numeric operations encountered on '{column}': {e}")
    except Exception as e:
        raise OutlierDetectionError(f"Failed to execute outlier detection on '{column}': {e}")


def run_duckdb_anomalies(df: pd.DataFrame) -> AnomalyReport:
    try:
        ctx = duckdb.connect(database=":memory:")
        ctx.register("df_view", df)

        null_cols: List[str] = []
        zero_cols: List[str] = []
        mismatches: List[Dict[str, Any]] = []

        total_rows = len(df)
        if total_rows == 0:
            return AnomalyReport(null_columns=[], all_zero_columns=[], type_mismatches=[])

        # Detect DuckDB version to pick the correct regex function
        version_str = ctx.execute("SELECT version()").fetchone()[0]  # e.g. "v0.10.3"
        try:
            major, minor = [int(x) for x in version_str.lstrip("v").split(".")[:2]]
        except Exception:
            major, minor = 0, 0

        # regexp_full_match introduced in DuckDB 0.10; use REGEXP_MATCHES for older versions
        if (major, minor) >= (0, 10):
            regex_fn = "regexp_full_match"
        else:
            regex_fn = "REGEXP_MATCHES"

        schema_res = ctx.execute("PRAGMA table_info('df_view')").fetchall()

        for col_info in schema_res:
            col_name = str(col_info[1])
            col_type = str(col_info[2])
            escaped_col = f'"{col_name}"'

            null_check = ctx.execute(
                f"SELECT COUNT(*) FROM df_view WHERE {escaped_col} IS NULL"
            ).fetchone()
            if null_check and null_check[0] == total_rows:
                null_cols.append(col_name)
                continue

            if col_type in ("BIGINT", "DOUBLE", "INTEGER", "HUGEINT", "FLOAT"):
                zero_check = ctx.execute(
                    f"SELECT COUNT(*) FROM df_view WHERE {escaped_col} = 0"
                ).fetchone()
                if zero_check and zero_check[0] == total_rows:
                    zero_cols.append(col_name)

            if col_type in ("VARCHAR", "TEXT"):
                numeric_pattern_query = f"""
                    SELECT COUNT(*) FROM df_view
                    WHERE {escaped_col} IS NOT NULL
                    AND TRY_CAST({escaped_col} AS DOUBLE) IS NOT NULL
                """
                num_pattern_cnt = ctx.execute(numeric_pattern_query).fetchone()
                if num_pattern_cnt and num_pattern_cnt[0] > 0 and num_pattern_cnt[0] < total_rows:
                    mismatches.append({
                        "column": col_name,
                        "issue": "Mixed numeric and text patterns detected",
                        "affected_rows": int(num_pattern_cnt[0])
                    })

                if "email" in col_name.lower():
                    email_regex = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
                    try:
                        email_fail_query = f"""
                            SELECT COUNT(*) FROM df_view
                            WHERE {escaped_col} IS NOT NULL
                            AND NOT {regex_fn}({escaped_col}, '{email_regex}')
                        """
                        email_fail_cnt = ctx.execute(email_fail_query).fetchone()
                        if email_fail_cnt and email_fail_cnt[0] > 0:
                            mismatches.append({
                                "column": col_name,
                                "issue": "Malformed structural email patterns",
                                "affected_rows": int(email_fail_cnt[0])
                            })
                    except duckdb.Error:
                        # Regex function unavailable — skip silently rather than returning 0
                        pass

                if "date" in col_name.lower():
                    date_fail_query = f"""
                        SELECT COUNT(*) FROM df_view
                        WHERE {escaped_col} IS NOT NULL
                        AND TRY_CAST({escaped_col} AS DATE) IS NULL
                        AND TRY_CAST({escaped_col} AS TIMESTAMP) IS NULL
                    """
                    date_fail_cnt = ctx.execute(date_fail_query).fetchone()
                    if date_fail_cnt and date_fail_cnt[0] > 0:
                        mismatches.append({
                            "column": col_name,
                            "issue": "Multi-format timeline sequences or corrupted string literals",
                            "affected_rows": int(date_fail_cnt[0])
                        })

        return AnomalyReport(
            null_columns=null_cols,
            all_zero_columns=zero_cols,
            type_mismatches=mismatches
        )
    except duckdb.Error as e:
        raise AnomalyDetectionError(f"DuckDB SQL engine runtime exception: {e}")
    except Exception as e:
        raise AnomalyDetectionError(f"Failed to process database anomaly detection: {e}")
