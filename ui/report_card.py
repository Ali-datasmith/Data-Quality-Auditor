# ui/report_card.py

from pathlib import Path
from typing import Any, Dict, List, TypedDict
import tomllib
import pandas as pd
import streamlit as st
from core.scorer import get_score_label
from ui.charts import render_distribution_histogram

class UIReportCardConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float

class UIReportCardConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int

class UIReportCardAppConfig(TypedDict):
    scoring: UIReportCardConfigScoring
    detection: UIReportCardConfigDetection

class UIReportCardException(Exception):
    pass

class UIReportCardConfigLoadError(UIReportCardException):
    pass

class ComponentRenderingError(UIReportCardException):
    pass

def load_ui_report_card_config() -> UIReportCardAppConfig:
    try:
        config_path = Path(__file__).resolve().parents[1] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f) # type: ignore
    except FileNotFoundError as e:
        raise UIReportCardConfigLoadError(f"Target configuration schema path missing: {e}")
    except tomllib.TOMLDecodeError as e:
        raise UIReportCardConfigLoadError(f"Corrupted TOML syntax format parameters: {e}")
    except Exception as e:
        raise UIReportCardConfigLoadError(f"Unexpected file operations context error: {e}")

_CONFIG: UIReportCardAppConfig = load_ui_report_card_config()

def render_column_card(col_name: str, col_stats: Dict[str, Any], col_score: int, df: pd.DataFrame) -> None:
    try:
        label_meta = get_score_label(col_score)
        header_text = f"{col_name} — Quality Index: {col_score}/100 [{label_meta.category}]"
        
        with st.expander(header_text, expanded=False):
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            with m_col1:
                st.metric(
                    label="Data Architecture Type",
                    value=str(col_stats.get("dtype", "Unknown"))
                )
            with m_col2:
                missing_pct = float(col_stats.get("missing_percentage", 0.0))
                st.metric(
                    label="Missing Value Factor",
                    value=f"{missing_pct:.2f}%",
                    delta=f"{int(col_stats.get('missing_count', 0))} rows" if missing_pct > 0 else None,
                    delta_color="inverse"
                )
            with m_col3:
                unique_cnt = int(col_stats.get("unique_count", 0))
                st.metric(
                    label="Unique Cardinality Scale",
                    value=f"{unique_cnt:,}"
                )
            with m_col4:
                outlier_cnt = int(col_stats.get("outlier_count", 0))
                st.metric(
                    label="Statistical Outlier Footprint",
                    value=f"{outlier_cnt:,}",
                    delta="Requires Review" if outlier_cnt > 0 else None,
                    delta_color="inverse"
                )
                
            st.markdown("---")
            v_col1, v_col2 = st.columns([1, 2])
            
            with v_col1:
                st.markdown("### Top Distribution Value Sets")
                top_values_list: List[Dict[str, Any]] = col_stats.get("top_values", [])
                if not top_values_list:
                    st.info("No categorical top frequencies extracted from variance map data profiles.")
                else:
                    distribution_records = [
                        {"Value Parameter": item.get("value"), "Occurrence Frequency": item.get("count")}
                        for item in top_values_list
                    ]
                    st.dataframe(
                        pd.DataFrame(distribution_records),
                        hide_index=True,
                        use_container_width=True
                    )
                    
            with v_col2:
                st.markdown("### Density Distribution Variance Mapping")
                if pd.api.types.is_numeric_dtype(df[col_name]):
                    render_distribution_histogram(df, col_name)
                else:
                    st.info("Selected feature vector dimension is non-numeric. Frequency array metrics plotted via tabular matrices layout.")
                    
    except KeyError as e:
        raise ComponentRenderingError(f"Missing essential dictionary keys during metric rendering cycle: {e}")
    except Exception as e:
        raise ComponentRenderingError(f"Failed to generate UI card component tracking architecture metrics: {e}")

def render_suggestion_box(suggestions: List[Any]) -> None:
    try:
        st.markdown("### Suggested Data Remediations Actions Pipeline")
        
        if not suggestions:
            st.success("No critical quality threshold violations logged. Dataset validation state optimal.")
            return
            
        display_records: List[Dict[str, Any]] = []
        for sug in suggestions:
            display_records.append({
                "Target Feature Axis": getattr(sug, "column", "All Columns"),
                "Remediation Operation": getattr(sug, "action_type", "UNKNOWN"),
                "Transformation Target Context": getattr(sug, "description", ""),
                "Estimated Scoring Impact": getattr(sug, "estimated_impact", "Low")
            })
            
        st.data_editor(
            pd.DataFrame(display_records),
            use_container_width=True,
            disabled=["Target Feature Axis", "Remediation Operation", "Transformation Target Context", "Estimated Scoring Impact"],
            key="suggestion_box_matrix_editor"
        )
    except AttributeError as e:
        raise ComponentRenderingError(f"Malformed analytical suggestion object properties mismatch: {e}")
    except Exception as e:
        raise ComponentRenderingError(f"Failed to render interactive workflow adjustment suggestions dashboard: {e}")
