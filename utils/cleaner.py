# utils/cleaner.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, TypedDict, Union
import tomllib
import io
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Config TypedDicts
# ---------------------------------------------------------------------------

class CleanerConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float


class CleanerConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int


class CleanerAppConfig(TypedDict):
    scoring: CleanerConfigScoring
    detection: CleanerConfigDetection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CleanerException(Exception):
    pass


class CleanerConfigLoadError(CleanerException):
    pass


class ProcessingError(CleanerException):
    pass


class ExportError(CleanerException):
    pass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CleaningSuggestion:
    id: str
    column: str
    action_type: str
    description: str
    estimated_impact: str


@dataclass(frozen=True)
class ChangeLogReport:
    initial_row_count: int
    final_row_count: int
    rows_dropped: int
    mutations_applied: Dict[str, int]
    structure_altered: bool


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_cleaner_config() -> CleanerAppConfig:
    try:
        config_path = Path(__file__).resolve().parents[1] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f)  # type: ignore
    except FileNotFoundError:
        return {
            "scoring": {
                "completeness_weight": 0.30,
                "uniqueness_weight":   0.20,
                "consistency_weight":  0.30,
                "outlier_weight":      0.20,
            },
            "detection": {
                "outlier_iqr_multiplier": 1.5,
                "max_upload_mb": 200,
            },
        }
    except tomllib.TOMLDecodeError as e:
        raise CleanerConfigLoadError(f"Invalid syntax configuration sequence: {e}")
    except Exception as e:
        raise CleanerConfigLoadError(f"Unexpected operational loading failure: {e}")


_CONFIG: CleanerAppConfig = load_cleaner_config()
_IQR_MULT: float = _CONFIG["detection"]["outlier_iqr_multiplier"]


# ---------------------------------------------------------------------------
# _is_date_column
# Helper to decide whether a column actually looks like dates —
# FIX: previously "object" in dtype matched EVERY string column
# (category, email, flagged, customer_id, etc.) and triggered
# NORMALIZE_DATE on all of them.  Now we only suggest it when:
#   (a) pandas already parsed it as datetime, OR
#   (b) the column name contains a date-like word, OR
#   (c) a sample parse succeeds on >50% of non-null values.
# ---------------------------------------------------------------------------

_DATE_NAME_HINTS = frozenset({"date", "time", "dt", "timestamp", "created", "updated", "joined", "dob"})


def _is_date_column(col_name: str, dtype: str, series: pd.Series) -> bool:
    # Already a proper datetime dtype
    if "datetime" in dtype:
        return True

    # Name contains a date-like hint word
    lower_name = col_name.lower()
    if any(hint in lower_name for hint in _DATE_NAME_HINTS):
        # Verify with a sample parse — avoids false positives on columns
        # that merely have "date" as part of a compound word (e.g. "mandate")
        non_null = series.dropna().astype(str)
        if non_null.empty:
            return False
        sample = non_null.head(20)
        parsed = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
        success_rate = parsed.notna().mean()
        return bool(success_rate >= 0.5)

    return False


# ---------------------------------------------------------------------------
# suggest_fixes
# FIX: NORMALIZE_DATE is now only suggested for genuine date columns,
#      not every column with dtype=="object".
# Dead function delete_placeholder_logic removed.
# ---------------------------------------------------------------------------

def suggest_fixes(
    profile: Dict[str, Any],
    duplicate_count: int = 0,
    source_df: Union[pd.DataFrame, None] = None,
) -> List[CleaningSuggestion]:
    """
    Returns a list of suggested cleaning actions per column.

    Parameters
    ----------
    profile         : enriched column stats dict from _build_enriched_profile
    duplicate_count : number of duplicate rows detected dataset-wide
    source_df       : the original DataFrame (used for date-column heuristic);
                      pass it in whenever available for best accuracy
    """
    try:
        suggestions: List[CleaningSuggestion] = []

        # Dataset-wide deduplication suggestion
        if duplicate_count > 0:
            suggestions.append(CleaningSuggestion(
                id="global_deduplicate",
                column="All Columns",
                action_type="DEDUPLICATE",
                description=f"Remove {duplicate_count} duplicate row footprints from dataset.",
                estimated_impact="High",
            ))

        for col_name, stats in profile.items():
            missing_cnt = int(stats.get("missing_count", 0))
            dtype       = str(stats.get("dtype", ""))

            # Pull the actual series if source_df is provided
            series: pd.Series = (
                source_df[col_name]
                if source_df is not None and col_name in source_df.columns
                else pd.Series(dtype=object)
            )

            # --- IMPUTE missing values ---
            if missing_cnt > 0:
                strategy = "median" if any(t in dtype for t in ("int", "float", "Int", "Float")) else "mode"
                suggestions.append(CleaningSuggestion(
                    id=f"impute_{col_name}",
                    column=col_name,
                    action_type="IMPUTE",
                    description=f"Fill {missing_cnt} missing values in '{col_name}' with column {strategy}.",
                    estimated_impact="Medium",
                ))

            # --- NORMALIZE_DATE — only for real date columns ---
            # FIX: was if "datetime" in dtype or "object" in dtype
            # which fired on EVERY string column. Now uses _is_date_column().
            if _is_date_column(col_name, dtype, series):
                suggestions.append(CleaningSuggestion(
                    id=f"normalize_{col_name}",
                    column=col_name,
                    action_type="NORMALIZE_DATE",
                    description=f"Standardise date formats in '{col_name}' to ISO-8601 YYYY-MM-DD.",
                    estimated_impact="Low",
                ))

            # --- CLAMP outliers — numeric only ---
            if any(t in dtype for t in ("int", "float", "Int", "Float")):
                outlier_cnt = int(stats.get("outlier_count", 0))
                if outlier_cnt > 0:
                    suggestions.append(CleaningSuggestion(
                        id=f"clamp_{col_name}",
                        column=col_name,
                        action_type="CLAMP_OUTLIERS",
                        description=(
                            f"Clamp {outlier_cnt} outlier(s) in '{col_name}' "
                            f"to IQR boundary limits."
                        ),
                        estimated_impact="Medium",
                    ))

        return suggestions

    except KeyError as e:
        raise ProcessingError(f"Missing diagnostic metrics in column stats dict: {e}")
    except Exception as e:
        raise ProcessingError(f"Failed to extract structural analysis suggestions: {e}")


# ---------------------------------------------------------------------------
# apply_fixes
# ---------------------------------------------------------------------------

def apply_fixes(
    df: pd.DataFrame,
    selected_fixes: List[Dict[str, Any]],
) -> pd.DataFrame:
    try:
        working_df = df.copy()

        for fix in selected_fixes:
            action = str(fix.get("action_type"))
            col    = str(fix.get("column"))

            if action == "DEDUPLICATE":
                working_df = working_df.drop_duplicates(keep="first").reset_index(drop=True)

            elif action == "IMPUTE" and col in working_df.columns:
                col_series = working_df[col]
                if pd.api.types.is_numeric_dtype(col_series):
                    fill_val = col_series.median()
                    working_df[col] = col_series.fillna(fill_val)
                else:
                    mode_val = col_series.mode()
                    if not mode_val.empty:
                        working_df[col] = col_series.fillna(mode_val[0])

            elif action == "NORMALIZE_DATE" and col in working_df.columns:
                working_df[col] = pd.to_datetime(
                    working_df[col], errors="coerce", infer_datetime_format=True
                )

            elif action == "CLAMP_OUTLIERS" and col in working_df.columns:
                col_series = working_df[col]
                if pd.api.types.is_numeric_dtype(col_series):
                    q25 = np.percentile(col_series.dropna(), 25)
                    q75 = np.percentile(col_series.dropna(), 75)
                    iqr = q75 - q25
                    lower_bound = q25 - (_IQR_MULT * iqr)
                    upper_bound = q75 + (_IQR_MULT * iqr)
                    working_df[col] = np.clip(col_series, lower_bound, upper_bound)

        return working_df

    except ValueError as e:
        raise ProcessingError(f"Value assignment error processing fix pipeline: {e}")
    except TypeError as e:
        raise ProcessingError(f"Type conflict in fix pipeline: {e}")
    except Exception as e:
        raise ProcessingError(f"Failed to apply fixes to dataset: {e}")


# ---------------------------------------------------------------------------
# export_cleaned_csv
# ---------------------------------------------------------------------------

def export_cleaned_csv(df: pd.DataFrame) -> bytes:
    try:
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        return buffer.getvalue()
    except Exception as e:
        raise ExportError(f"Failed to serialize cleaned dataframe to CSV bytes: {e}")


# ---------------------------------------------------------------------------
# generate_change_log
# ---------------------------------------------------------------------------

def generate_change_log(
    original_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
) -> ChangeLogReport:
    try:
        initial_rows = len(original_df)
        final_rows   = len(cleaned_df)
        dropped      = max(0, initial_rows - final_rows)
        mutations: Dict[str, int] = {}

        for col in original_df.columns:
            if col not in cleaned_df.columns:
                continue

            orig_nulls  = int(original_df[col].isna().sum())
            clean_nulls = int(cleaned_df[col].isna().sum())
            imputed     = max(0, orig_nulls - clean_nulls)
            if imputed > 0:
                mutations[f"{col}_imputed_values"] = imputed

            if (
                pd.api.types.is_numeric_dtype(original_df[col])
                and pd.api.types.is_numeric_dtype(cleaned_df[col])
            ):
                compare_len = min(initial_rows, final_rows)
                mismatches  = int(
                    (
                        original_df[col].values[:compare_len]
                        != cleaned_df[col].values[:compare_len]
                    ).sum()
                )
                clamped = max(0, mismatches - imputed)
                if clamped > 0:
                    mutations[f"{col}_clamped_outliers"] = clamped

        structural_alteration = set(original_df.columns) != set(cleaned_df.columns)

        return ChangeLogReport(
            initial_row_count=initial_rows,
            final_row_count=final_rows,
            rows_dropped=dropped,
            mutations_applied=mutations,
            structure_altered=structural_alteration,
        )

    except KeyError as e:
        raise ProcessingError(f"Column index divergence in change log: {e}")
    except Exception as e:
        raise ProcessingError(f"Failed to assemble change log report: {e}")
