# utils/cleaner.py

import re
import uuid
from typing import Any, NamedTuple

import pandas as pd
import polars as pl

_AUDIT_ROW_ID_PATTERN = re.compile(r"^__dq_audit_row_id_[0-9a-f]{12}__$")


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
        dtype_str = str(stats.get("dtype", "")).lower()
        is_temporal = any(
            token in dtype_str
            for token in ("date", "datetime", "time", "duration", "timestamp")
        )
        if stats.get("missing_count", 0) > 0 and not is_temporal:
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
    """Applies remediation fixes lazily using Polars pl.LazyFrame with type safety and collision-safe row id tracking."""
    schema = lf.collect_schema()
    existing_cols = set(schema.names())

    audit_row_id = f"__dq_audit_row_id_{uuid.uuid4().hex[:12]}__"
    while audit_row_id in existing_cols:
        audit_row_id = f"__dq_audit_row_id_{uuid.uuid4().hex[:12]}__"

    lf = lf.with_row_index(audit_row_id)
    original_user_cols = [c for c in schema.names() if c != audit_row_id]

    drop_dups = any(fix.get("action_type") == "DROP_DUPLICATES" for fix in fixes)
    if drop_dups:
        lf = lf.unique(subset=original_user_cols if original_user_cols else None, keep="first")

    exprs: list[pl.Expr] = [pl.col(audit_row_id)]

    for col in original_user_cols:
        dtype = schema[col]
        col_expr = pl.col(col)

        missing_fix = next(
            (f for f in fixes if f.get("action_type") == "FILL_MISSING" and f.get("column") == col),
            None,
        )
        if missing_fix:
            if dtype.is_numeric() and dtype != pl.Boolean:
                fallback_lit = pl.lit(0) if dtype.is_integer() else pl.lit(0.0)
                col_expr = col_expr.fill_null(pl.col(col).median()).fill_null(fallback_lit)
            elif dtype == pl.Boolean:
                col_expr = col_expr.fill_null(pl.lit(False))
            elif dtype.is_temporal():
                pass
            else:
                col_expr = col_expr.fill_null(pl.lit("Unknown"))

        outlier_fix = next(
            (f for f in fixes if f.get("action_type") == "CAP_OUTLIERS" and f.get("column") == col),
            None,
        )
        if outlier_fix and dtype.is_numeric() and dtype != pl.Boolean:
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
    """Eager wrapper that uses Polars lazy execution internally and preserves audit row identity."""
    if isinstance(df, pd.DataFrame):
        lf = pl.from_pandas(df).lazy()
    else:
        lf = df.lazy()

    cleaned_lf = apply_fixes_lazy(lf, fixes)
    res_df = cleaned_lf.collect().to_pandas()

    audit_col = next((c for c in res_df.columns if _AUDIT_ROW_ID_PATTERN.match(str(c))), None)
    if audit_col:
        res_df = res_df.set_index(audit_col, drop=True)
        res_df.index.name = None
    return res_df


def generate_change_log(
    active_df: pd.DataFrame,
    cleaned: pd.DataFrame,
) -> ChangeLog:
    rows_dropped = max(0, len(active_df) - len(cleaned))
    mutations: dict[str, int] = {}

    common_idx = active_df.index.intersection(cleaned.index)
    for col in active_df.columns:
        if col in cleaned.columns:
            orig_vals = active_df.loc[common_idx, col]
            clean_vals = cleaned.loc[common_idx, col]

            filled_mask = orig_vals.isna() & clean_vals.notna()
            modified_mask = orig_vals.notna() & clean_vals.notna() & (orig_vals != clean_vals)
            nullified_mask = orig_vals.notna() & clean_vals.isna()

            mutations[col] = int((filled_mask | modified_mask | nullified_mask).sum())
        else:
            mutations[col] = 0

    return ChangeLog(rows_dropped=rows_dropped, mutations_applied=mutations)


def export_cleaned_csv(cleaned_df: pd.DataFrame | pl.DataFrame) -> bytes:
    if isinstance(cleaned_df, pl.DataFrame):
        audit_cols = [c for c in cleaned_df.columns if _AUDIT_ROW_ID_PATTERN.match(str(c))]
        if audit_cols:
            cleaned_df = cleaned_df.drop(audit_cols)
        res = cleaned_df.write_csv()
        return res.encode("utf-8") if isinstance(res, str) else res

    audit_cols = [c for c in cleaned_df.columns if _AUDIT_ROW_ID_PATTERN.match(str(c))]
    if audit_cols:
        cleaned_df = cleaned_df.drop(columns=audit_cols)
    return cleaned_df.to_csv(index=False).encode("utf-8")


def sink_cleaned_csv(cleaned_lf: pl.LazyFrame, output_path: str) -> None:
    """Streams cleaned data directly to a CSV file on disk using Polars sink_csv."""
    cleaned_lf.sink_csv(output_path)
