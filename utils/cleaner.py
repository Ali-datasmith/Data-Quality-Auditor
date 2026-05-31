# utils/cleaner.py

import io
from typing import Any, Dict, List, NamedTuple
import pandas as pd

class RemediationSuggestion:
    def __init__(self, column: str, action_type: str, description: str, estimated_impact: str, details: Dict[str, Any] = None):
        self.column = column
        self.action_type = action_type
        self.description = description
        self.estimated_impact = estimated_impact
        self.details = details or {}

class ChangeLog(NamedTuple):
    rows_dropped: int
    mutations_applied: Dict[str, int]

def suggest_fixes(profile: Dict[str, Dict[str, Any]], duplicate_count: int, source_df: pd.DataFrame) -> List[RemediationSuggestion]:
    suggestions: List[RemediationSuggestion] = []
    
    if duplicate_count > 0:
        suggestions.append(RemediationSuggestion(
            column="All Columns",
            action_type="DROP_DUPLICATES",
            description=f"Purge {duplicate_count} structural multi-row duplicate occurrences across full table index context.",
            estimated_impact="High"
        ))
        
    for col, stats in profile.items():
        if stats.get("missing_count", 0) > 0:
            suggestions.append(RemediationSuggestion(
                column=col,
                action_type="FILL_MISSING",
                description=f"Impute {stats['missing_count']} blank missing fields using statistical central tendency configurations.",
                estimated_impact="Medium",
                details={"dtype": str(stats["dtype"])}
            ))
        if stats.get("outlier_count", 0) > 0:
            suggestions.append(RemediationSuggestion(
                column=col,
                action_type="CAP_OUTLIERS",
                description=f"Clamp {stats['outlier_count']} variance outliers safely inside calculated IQR constraints boundaries.",
                estimated_impact="Medium",
                details={"lower_fence": stats.get("lower_fence"), "upper_fence": stats.get("upper_fence")}
            ))
    return suggestions

def apply_fixes(df: pd.DataFrame, fixes: List[Dict[str, Any]]) -> pd.DataFrame:
    cleaned_df = df.copy()
    
    for fix in fixes:
        action = fix.get("action_type")
        col = fix.get("column")
        details = fix.get("details", {})
        
        if action == "DROP_DUPLICATES":
            cleaned_df.drop_duplicates(inplace=True)
            
        elif action == "FILL_MISSING" and col in cleaned_df.columns:
            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                fill_val = cleaned_df[col].median()
            else:
                fill_val = cleaned_df[col].mode()[0] if not cleaned_df[col].mode().empty else "Unknown"
            cleaned_df[col] = cleaned_df[col].fillna(fill_val)
            
        elif action == "CAP_OUTLIERS" and col in cleaned_df.columns:
            low = details.get("lower_fence")
            high = details.get("upper_fence")
            if low is not None and high is not None:
                cleaned_df[col] = cleaned_df[col].clip(lower=float(low), upper=float(high))
                
    return cleaned_df

def generate_change_log(active_df: pd.DataFrame, cleaned: pd.DataFrame) -> ChangeLog:
    rows_dropped = max(0, len(active_df) - len(cleaned))
    mutations: Dict[str, int] = {}
    
    common_idx = active_df.index.intersection(cleaned.index)
    for col in active_df.columns:
        if col in cleaned.columns:
            diff_mask = (active_df.loc[common_idx, col] != cleaned.loc[common_idx, col]) & ~(active_df.loc[common_idx, col].isna() & cleaned.loc[common_idx, col].isna())
            filled_mask = active_df.loc[common_idx, col].isna() & ~cleaned.loc[common_idx, col].isna()
            mutations[col] = int(diff_mask.sum() + filled_mask.sum())
        else:
            mutations[col] = 0
            
    return ChangeLog(rows_dropped=rows_dropped, mutations_applied=mutations)

def export_cleaned_csv(cleaned_df: pd.DataFrame) -> bytes:
    return cleaned_df.to_csv(index=False).encode("utf-8")
