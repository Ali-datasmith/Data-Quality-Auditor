# ui/report_card.py

from pathlib import Path
from typing import Any, TypedDict
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
        raise UIReportCardConfigLoadError(f"Corrupted TOML syntax format parameters: {e}")


_CONFIG: UIReportCardAppConfig = load_ui_report_card_config()


def render_column_card(
    col_name: str,
    col_stats: dict[str, Any],
    col_score: int,
    df: pd.DataFrame,
) -> None:
    try:
        label_meta = get_score_label(col_score)
        header_text = f"{col_name} — Quality: {col_score}/100 [{label_meta.category}]"

        with st.expander(header_text, expanded=False):
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)

            with m_col1:
                st.metric(
                    label="Type",
                    value=str(col_stats.get("dtype", "Unknown"))
                )
            with m_col2:
                missing_pct = float(col_stats.get("missing_percentage", 0.0))
                st.metric(
                    label="Missing %",
                    value=f"{missing_pct:.2f}%",
                    delta=f"{int(col_stats.get('missing_count', 0))} rows" if missing_pct > 0 else None,
                    delta_color="inverse"
                )
            with m_col3:
                unique_cnt = int(col_stats.get("unique_count", 0))
                st.metric(
                    label="Unique",
                    value=f"{unique_cnt:,}"
                )
            with m_col4:
                outlier_cnt = int(col_stats.get("outlier_count", 0))
                st.metric(
                    label="Outliers",
                    value=f"{outlier_cnt:,}",
                    delta="Needs Review" if outlier_cnt > 0 else None,
                    delta_color="inverse"
                )

            st.markdown("---")
            v_col1, v_col2 = st.columns([1, 2])

            with v_col1:
                st.markdown("### Top Values")
                top_values_list: list[dict[str, Any]] = col_stats.get("top_values", [])
                if not top_values_list:
                    st.info("No values to display.")
                else:
                    distribution_records = [
                        {"Value": item.get("value"), "Count": item.get("count")}
                        for item in top_values_list
                    ]
                    st.dataframe(
                        pd.DataFrame(distribution_records),
                        hide_index=True,
                        use_container_width=True
                    )

            with v_col2:
                st.markdown("### Distribution")
                if pd.api.types.is_numeric_dtype(df[col_name]) and not pd.api.types.is_bool_dtype(df[col_name]):
                    render_distribution_histogram(df, col_name)
                else:
                    st.info("Non-numeric or boolean column — distribution chart skipped.")

    except KeyError as e:
        raise ComponentRenderingError(f"Missing essential dictionary keys during metric rendering: {e}")
    except Exception as e:
        raise ComponentRenderingError(f"Failed to generate UI card component tracking architecture metrics: {e}")


def render_suggestion_box(suggestions: list[Any]) -> None:
    try:
        st.markdown("### Suggested Remediations")

        if not suggestions:
            st.success("No critical issues. Dataset is clean.")
            return

        display_records: list[dict[str, Any]] = []
        for sug in suggestions:
            display_records.append({
                "Column":   sug.column if hasattr(sug, "column") else sug.get("column", ""),
                "Action":   sug.action_type if hasattr(sug, "action_type") else sug.get("action_type", ""),
                "Details":  sug.description if hasattr(sug, "description") else sug.get("description", ""),
                "Impact":   sug.estimated_impact if hasattr(sug, "estimated_impact") else sug.get("estimated_impact", ""),
            })

        st.dataframe(
            pd.DataFrame(display_records),
            use_container_width=True,
            hide_index=True,
        )

    except Exception as e:
        raise ComponentRenderingError(f"Failed to generate suggestion box panel: {e}")
