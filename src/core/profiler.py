# core/profiler.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import duckdb
import numpy as np
import pandas as pd
import polars as pl
import tomllib


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
    mean_value: float | None
    std_value: float | None
    top_values: list[dict[str, Any]]


@dataclass(frozen=True)
class DuplicateReport:
    count: int
    indices: list[int]


@dataclass(frozen=True)
class OutlierReport:
    count: int
    indices: list[int]
    lower_fence: float
    upper_fence: float


@dataclass(frozen=True)
class AnomalyReport:
    null_columns: list[str]
    all_zero_columns: list[str]
    type_mismatches: list[dict[str, Any]]


def load_config() -> AppConfig:
    try:
        # Resolve config.toml at repo root (two levels up from src/core/profiler.py)
        config_path = Path(__file__).resolve().parents[2] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f)  # type: ignore
    except FileNotFoundError:
        return {
            "scoring": {
                "completeness_weight": 0.3,
                "uniqueness_weight": 0.2,
                "consistency_weight": 0.3,
                "outlier_weight": 0.2,
            },
            "detection": {
                "outlier_iqr_multiplier": 1.5,
                "max_upload_mb": 200,
            },
        }
    except tomllib.TOMLDecodeError as e:
        raise ProfilerError(f"Invalid TOML in configuration file: {e}")


_CONFIG: AppConfig = load_config()
_IQR_MULTIPLIER: float = _CONFIG["detection"]["outlier_iqr_multiplier"]


def scan_file_lazy(path: Path | str) -> pl.LazyFrame:
    """Scans a CSV lazily using Polars pl.scan_csv for zero-copy memory optimization."""
    try:
        return pl.scan_csv(path, infer_schema_length=10000, try_parse_dates=True)
    except Exception as e:
        raise FileLoadError(f"Polars failed to scan CSV lazily: {e}")


def load_file(path: Path | str) -> pd.DataFrame:
    try:
        lf = scan_file_lazy(path)
        return lf.collect().to_pandas()
    except Exception as e:
        raise FileLoadError(f"Unexpected error loading file: {e}")


def _get_lazyframe(df_or_lf: pd.DataFrame | pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    """Helper to ensure input data is converted to a Polars LazyFrame."""
    if isinstance(df_or_lf, pl.LazyFrame):
        return df_or_lf
    if isinstance(df_or_lf, pl.DataFrame):
        return df_or_lf.lazy()
    if isinstance(df_or_lf, pd.DataFrame):
        return pl.from_pandas(df_or_lf).lazy()
    raise ProfileGenerationError(f"Unsupported data structure type: {type(df_or_lf)}")


def generate_profile(df_or_lf: pd.DataFrame | pl.DataFrame | pl.LazyFrame) -> dict[str, ColumnProfile]:
    try:
        lf = _get_lazyframe(df_or_lf)
        schema = lf.collect_schema()

        # Calculate total row count lazily
        total_rows = lf.select(pl.len()).collect().item()

        profile_results: dict[str, ColumnProfile] = {}

        if total_rows == 0:
            for col, dtype in schema.items():
                profile_results[str(col)] = ColumnProfile(
                    dtype=str(dtype),
                    missing_count=0,
                    missing_percentage=0.0,
                    unique_count=0,
                    min_value=None,
                    max_value=None,
                    mean_value=None,
                    std_value=None,
                    top_values=[],
                )
            return profile_results

        # Aggregate missing count, n_unique, min, max, mean, std lazily across all columns
        agg_exprs = []
        for col, dtype in schema.items():
            agg_exprs.extend([
                pl.col(col).null_count().alias(f"{col}__null_count"),
                pl.col(col).n_unique().alias(f"{col}__n_unique"),
                pl.col(col).min().alias(f"{col}__min"),
                pl.col(col).max().alias(f"{col}__max"),
            ])
            if dtype.is_numeric():
                agg_exprs.extend([
                    pl.col(col).mean().alias(f"{col}__mean"),
                    pl.col(col).std().alias(f"{col}__std"),
                ])

        metrics_df = lf.select(agg_exprs).collect()

        for col, dtype in schema.items():
            missing_cnt = int(metrics_df[f"{col}__null_count"].item())
            missing_pct = float((missing_cnt / total_rows) * 100) if total_rows > 0 else 0.0
            unique_cnt = int(metrics_df[f"{col}__n_unique"].item())

            # Top 5 value counts using Polars lazy execution
            try:
                top_df = (
                    lf.select(pl.col(col))
                    .drop_nulls()
                    .group_by(col)
                    .len()
                    .sort("len", descending=True)
                    .limit(5)
                    .collect()
                )
                top_vals = [
                    {"value": str(row[0]), "count": int(row[1])}
                    for row in top_df.iter_rows()
                ]
            except Exception:
                top_vals = []

            min_v = metrics_df[f"{col}__min"].item()
            max_v = metrics_df[f"{col}__max"].item()

            if dtype.is_numeric():
                mean_v_raw = metrics_df[f"{col}__mean"].item()
                std_v_raw = metrics_df[f"{col}__std"].item()

                mean_v = float(mean_v_raw) if mean_v_raw is not None and not np.isnan(mean_v_raw) else None
                std_v = float(std_v_raw) if std_v_raw is not None and not np.isnan(std_v_raw) else None
                min_v = float(min_v) if min_v is not None and not np.isnan(min_v) else None
                max_v = float(max_v) if max_v is not None and not np.isnan(max_v) else None
            else:
                mean_v = None
                std_v = None
                min_v = str(min_v) if min_v is not None else None
                max_v = str(max_v) if max_v is not None else None

            profile_results[str(col)] = ColumnProfile(
                dtype=str(dtype),
                missing_count=missing_cnt,
                missing_percentage=missing_pct,
                unique_count=unique_cnt,
                min_value=min_v,
                max_value=max_v,
                mean_value=mean_v,
                std_value=std_v,
                top_values=top_vals,
            )

        return profile_results
    except Exception as e:
        raise ProfileGenerationError(f"Failed to generate dataframe profile: {e}")


def detect_duplicates(df_or_lf: pd.DataFrame | pl.DataFrame | pl.LazyFrame, subset: list[str] | None = None) -> DuplicateReport:
    try:
        lf = _get_lazyframe(df_or_lf)

        # Attach row index lazily and find duplicate rows
        indexed_lf = lf.with_row_index("__row_id__")

        cols = subset if subset else [c for c in lf.collect_schema().names()]
        if not cols:
            return DuplicateReport(count=0, indices=[])

        # Filter duplicates where count > 1 and row_id != first row_id in group
        dup_indices_df = (
            indexed_lf.with_columns(
                pl.int_range(0, pl.len()).over(cols).alias("__dup_rank__")
            )
            .filter(pl.col("__dup_rank__") > 0)
            .select("__row_id__")
            .collect()
        )

        indices = [int(x) for x in dup_indices_df["__row_id__"].to_list()]
        return DuplicateReport(count=len(indices), indices=indices)
    except Exception as e:
        raise DuplicateDetectionError(f"Failed to detect duplicate rows: {e}")


def detect_outliers(df_or_lf: pd.DataFrame | pl.DataFrame | pl.LazyFrame, column: str, iqr_multiplier: float | None = None) -> OutlierReport:
    try:
        lf = _get_lazyframe(df_or_lf)
        schema = lf.collect_schema()

        if column not in schema:
            raise OutlierDetectionError(f"Target column '{column}' not found for outlier analysis")

        dtype = schema[column]
        multiplier = iqr_multiplier if iqr_multiplier is not None else _IQR_MULTIPLIER

        # Skip non-numeric and boolean types
        if not dtype.is_numeric() or dtype == pl.Boolean:
            return OutlierReport(count=0, indices=[], lower_fence=0.0, upper_fence=0.0)

        # Compute quantiles lazily
        quantiles = lf.select([
            pl.col(column).quantile(0.25).alias("q25"),
            pl.col(column).quantile(0.75).alias("q75")
        ]).collect()

        q25 = quantiles["q25"].item()
        q75 = quantiles["q75"].item()

        if q25 is None or q75 is None or np.isnan(q25) or np.isnan(q75):
            return OutlierReport(count=0, indices=[], lower_fence=0.0, upper_fence=0.0)

        iqr = float(q75 - q25)
        lower_fence = float(q25 - (multiplier * iqr))
        upper_fence = float(q75 + (multiplier * iqr))

        outliers_df = (
            lf.with_row_index("__row_id__")
            .filter((pl.col(column) < lower_fence) | (pl.col(column) > upper_fence))
            .select("__row_id__")
            .collect()
        )

        indices = [int(x) for x in outliers_df["__row_id__"].to_list()]
        return OutlierReport(
            count=len(indices),
            indices=indices,
            lower_fence=lower_fence,
            upper_fence=upper_fence,
        )
    except Exception as e:
        if isinstance(e, OutlierDetectionError):
            raise
        raise OutlierDetectionError(f"Failed to execute outlier detection on '{column}': {e}")


def run_duckdb_anomalies(df_or_lf: pd.DataFrame | pl.DataFrame | pl.LazyFrame) -> AnomalyReport:
    try:
        if isinstance(df_or_lf, pd.DataFrame):
            df = df_or_lf
        elif isinstance(df_or_lf, pl.DataFrame):
            df = df_or_lf.to_pandas()
        elif isinstance(df_or_lf, pl.LazyFrame):
            df = df_or_lf.collect().to_pandas()
        else:
            raise AnomalyDetectionError(f"Unsupported data input type: {type(df_or_lf)}")

        ctx = duckdb.connect(database=":memory:")
        ctx.register("df_view", df)

        null_cols: list[str] = []
        zero_cols: list[str] = []
        mismatches: list[dict[str, Any]] = []

        total_rows = len(df)
        if total_rows == 0:
            return AnomalyReport(null_columns=[], all_zero_columns=[], type_mismatches=[])

        version_str = ctx.execute("SELECT version()").fetchone()[0]  # type: ignore
        try:
            major, minor = [int(x) for x in version_str.lstrip("v").split(".")[:2]]
        except Exception:
            major, minor = 0, 0

        regex_fn = "regexp_full_match" if (major, minor) >= (0, 10) else "REGEXP_MATCHES"

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
                if num_pattern_cnt and 0 < num_pattern_cnt[0] < total_rows:
                    mismatches.append({
                        "column": col_name,
                        "issue": "Mixed numeric and text patterns detected",
                        "affected_rows": int(num_pattern_cnt[0]),
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
                                "affected_rows": int(email_fail_cnt[0]),
                            })
                    except duckdb.Error:
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
                            "affected_rows": int(date_fail_cnt[0]),
                        })

        return AnomalyReport(
            null_columns=null_cols,
            all_zero_columns=zero_cols,
            type_mismatches=mismatches,
        )
    except duckdb.Error as e:
        raise AnomalyDetectionError(f"DuckDB SQL engine runtime exception: {e}")
    except Exception as e:
        raise AnomalyDetectionError(f"Failed to process database anomaly detection: {e}")
