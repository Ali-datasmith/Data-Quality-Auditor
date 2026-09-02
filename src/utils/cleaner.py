# utils/cleaner.py

from typing import Any, NamedTuple

import pandas as pd
import polars as pl


class RemediationSuggestion:
    def __init__(
        self,
        column: str,
        action_type: str,
        description: str,
        estimated_impact: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.column = column
        self.action_type = action_type
        self.description = description
        self.estimated_impact = estimated_impact
        self.details = details or {}


class ChangeLog(NamedTuple):
    rows_dropped: int
    mutations_applied: dict[str, int]


def suggest_fixes(
    profile: dict[str, dict[str, Any]],
    duplicate_count: int,
    source_df: pd.DataFrame | pl.DataFrame | pl.LazyFrame | None = None,
) -> list[RemediationSuggestion]:
    suggestions: list[RemediationSuggestion] = []

    if duplicate_count > 0:
        suggestions.append(RemediationSuggestion(
            column="All Columns",
            action_type="DROP_DUPLICATES",
            description=f"Purge {duplicate_count} structural multi-row duplicate occurrences across full table index context.",
            estimated_impact="High",
        ))

    for col, stats in profile.items():
        if stats.get("missing_count", 0) > 0:
            suggestions.append(RemediationSuggestion(
                column=col,
                action_type="FILL_MISSING",
                description=f"Impute {stats['missing_count']} blank missing fields using statistical central tendency configurations.",
                estimated_impact="Medium",
                details={"dtype": str(stats.get("dtype", ""))}
            ))
        if stats.get("outlier_count", 0) > 0:
            suggestions.append(RemediationSuggestion(
                column=col,
                action_type="CAP_OUTLIERS",
                description=f"Clamp {stats['outlier_count']} variance outliers safely inside calculated IQR constraints boundaries.",
                estimated_impact="Medium",
                details={
                    "lower_fence": stats.get("lower_fence"),
                    "upper_fence": stats.get("upper_fence"),
                },
            ))
    return suggestions


def apply_fixes_lazy(
    lf: pl.LazyFrame,
    fixes: list[dict[str, Any]],
) -> pl.LazyFrame:
    """Applies remediation fixes lazily using Polars pl.LazyFrame."""
    schema = lf.collect_schema()
    exprs: list[pl.Expr] = []

    drop_dups = any(fix.get("action_type") == "DROP_DUPLICATES" for fix in fixes)
    if drop_dups:
        # Polars LazyFrame doesn't have drop_duplicates directly; unique() is used on LazyFrame
        lf = lf.unique()

    for col, dtype in schema.items():
        col_expr = pl.col(col)

        # Check for FILL_MISSING for this column
        missing_fix = next(
            (f for f in fixes if f.get("action_type") == "FILL_MISSING" and f.get("column") == col),
            None,
        )
        if missing_fix:
            if dtype.is_numeric():
                col_expr = col_expr.fill_null(pl.col(col).median())
            else:
                col_expr = col_expr.fill_null(pl.lit("Unknown"))

        # Check for CAP_OUTLIERS for this column
        outlier_fix = next(
            (f for f in fixes if f.get("action_type") == "CAP_OUTLIERS" and f.get("column") == col),
            None,
        )
        if outlier_fix:
            details = outlier_fix.get("details", {})
            low = details.get("lower_fence")
            high = details.get("upper_fence")
            if low is not None and high is not None:
                col_expr = col_expr.clip(float(low), float(high))

        exprs.append(col_expr.alias(col))

    return lf.select(exprs)


def apply_fixes(
    df: pd.DataFrame | pl.DataFrame,
    fixes: list[dict[str, Any]],
) -> pd.DataFrame:
    """Eager wrapper that uses Polars lazy execution internally for maximum performance."""
    if isinstance(df, pd.DataFrame):
        lf = pl.from_pandas(df).lazy()
        cleaned_lf = apply_fixes_lazy(lf, fixes)
        return cleaned_lf.collect().to_pandas()

    lf = df.lazy()
    cleaned_lf = apply_fixes_lazy(lf, fixes)
    return cleaned_lf.collect().to_pandas()


def generate_change_log(
    active_df: pd.DataFrame,
    cleaned: pd.DataFrame,
) -> ChangeLog:
    rows_dropped = max(0, len(active_df) - len(cleaned))
    mutations: dict[str, int] = {}

    common_idx = active_df.index.intersection(cleaned.index)
    for col in active_df.columns:
        if col in cleaned.columns:
            diff_mask = (
                (active_df.loc[common_idx, col] != cleaned.loc[common_idx, col])
                & ~(active_df.loc[common_idx, col].isna() & cleaned.loc[common_idx, col].isna())
            )
            filled_mask = active_df.loc[common_idx, col].isna() & ~cleaned.loc[common_idx, col].isna()
            mutations[col] = int(diff_mask.sum() + filled_mask.sum())
        else:
            mutations[col] = 0

    return ChangeLog(rows_dropped=rows_dropped, mutations_applied=mutations)


def export_cleaned_csv(cleaned_df: pd.DataFrame | pl.DataFrame) -> bytes:
    if isinstance(cleaned_df, pl.DataFrame):
        return cleaned_df.write_csv().encode("utf-8")
    return cleaned_df.to_csv(index=False).encode("utf-8")


def sink_cleaned_csv(cleaned_lf: pl.LazyFrame, output_path: str) -> None:
    """Streams cleaned data directly to a CSV file on disk using Polars sink_csv for low memory footprint."""
    cleaned_lf.sink_csv(output_path)
