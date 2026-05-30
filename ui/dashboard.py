# ui/dashboard.py

from pathlib import Path
from typing import Any, Dict, List, TypedDict
import tomllib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from core.scorer import get_score_label, QualityIssue

class UIDashboardConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float

class UIDashboardConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int

class UIDashboardAppConfig(TypedDict):
    scoring: UIDashboardConfigScoring
    detection: UIDashboardConfigDetection

class UIDashboardException(Exception):
    pass

class UIDashboardConfigLoadError(UIDashboardException):
    pass

class DashboardRenderingError(UIDashboardException):
    pass

def load_ui_dashboard_config() -> UIDashboardAppConfig:
    try:
        config_path = Path(__file__).resolve().parents[1] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f) # type: ignore
    except FileNotFoundError as e:
        raise UIDashboardConfigLoadError(f"Target path mapping configurations missing: {e}")
    except tomllib.TOMLDecodeError as e:
        raise UIDashboardConfigLoadError(f"Malformed schema file parsing parameters: {e}")
    except Exception as e:
        raise UIDashboardConfigLoadError(f"Unexpected operational layout setup failure: {e}")

_CONFIG: UIDashboardAppConfig = load_ui_dashboard_config()

_THEME: Dict[str, Any] = {
    "font": {"family": "Inter, sans-serif", "color": "#FAFAFA"},
    "paper_bgcolor": "#0E1117",
    "plot_bgcolor": "#161A24",
    "margin": {"l": 30, "r": 30, "t": 40, "b": 30}
}

def render_overview_metrics(score: int, profile: Dict[str, Dict[str, Any]], issues: List[QualityIssue]) -> None:
    try:
        if not profile:
            return
            
        first_col = next(iter(profile.values()))
        total_rows = int(first_col.get("total_rows", 0))
        total_cols = len(profile)
        issue_count = len(issues)
        label_meta = get_score_label(score)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(label="Overall Quality Index", value=f"{score}/100", delta=label_meta.category)
        with c2:
            st.metric(label="Total Logged Rows", value=f"{total_rows:,}")
        with c3:
            st.metric(label="Total Feature Columns", value=f"{total_cols}")
        with c4:
            st.metric(label="Detected Issue Indicators", value=f"{issue_count}", delta="Requires Fix" if issue_count > 0 else "Clean", delta_color="inverse" if issue_count > 0 else "normal")
    except Exception as e:
        raise DashboardRenderingError(f"Failed to render core overview status metrics layout panels: {e}")

def render_score_gauge(score: int) -> None:
    try:
        label_meta = get_score_label(score)
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            number={"font": {"size": 48, "color": "#FAFAFA"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#FAFAFA"},
                "bar": {"color": label_meta.color_hex},
                "bgcolor": "#161A24",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 30], "color": "rgba(231, 76, 60, 0.1)"},
                    {"range": [30, 50], "color": "rgba(230, 126, 34, 0.1)"},
                    {"range": [50, 70], "color": "rgba(241, 196, 15, 0.1)"},
                    {"range": [70, 90], "color": "rgba(52, 152, 218, 0.1)"},
                    {"range": [90, 100], "color": "rgba(46, 204, 113, 0.1)"}
                ]
            }
        ))
        
        fig.update_layout(
            font=_THEME["font"],
            paper_bgcolor=_THEME["paper_bgcolor"],
            margin=_THEME["margin"],
            height=250
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        raise DashboardRenderingError(f"Failed to generate dial gauge mapping visualization parameters: {e}")

def render_column_table(profile: Dict[str, Dict[str, Any]], scores: Dict[str, int]) -> None:
    try:
        table_records: List[Dict[str, Any]] = []
        
        for col_name, stats in profile.items():
            col_score = scores.get(col_name, 0)
            missing_cnt = int(stats.get("missing_count", 0))
            outlier_cnt = int(stats.get("outlier_count", 0))
            mismatch_cnt = int(stats.get("mismatch_count", 0))
            
            badges: List[str] = []
            if missing_cnt > 0: badges.append("🚨 Missing")
            if outlier_cnt > 0: badges.append("📊 Outliers")
            if mismatch_cnt > 0: badges.append("⚠️ Type Mismatch")
            if not badges: badges.append("✅ Clear")
                
            table_records.append({
                "Feature Axis": col_name,
                "Data Type": str(stats.get("dtype", "Unknown")),
                "Quality Index Score": col_score,
                "Missing Values Count": missing_cnt,
                "Outlier Metrics Count": outlier_cnt,
                "Integrity Issues Indicators": ", ".join(badges)
            })
            
        summary_df = pd.DataFrame(table_records).sort_values(by="Quality Index Score", ascending=True)
        
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Quality Index Score": st.column_config.ProgressColumn(
                    "Quality Index Score",
                    help="Calculated granular column validity baseline weights mapping",
                    format="%d",
                    min_value=0,
                    max_value=100
                )
            }
        )
    except Exception as e:
        raise DashboardRenderingError(f"Failed to generate data matrix summary tracking grids: {e}")

def render_issue_list(issues: List[QualityIssue]) -> None:
    try:
        st.markdown("### Severity Sorted Database Integrity Issues Logs")
        
        if not issues:
            st.success("Zero anomalous parameters recorded across system layout thresholds.")
            return
            
        for issue in issues:
            severity_color = "#E74C3C" if issue.severity == "Critical" else ("#E67E22" if issue.severity == "High" else "#F1C40F")
            
            markdown_block = (
                f'<div style="border-left: 4px solid {severity_color}; padding-left: 15px; margin-bottom: 12px;">'
                f'<span style="font-weight: bold; color: {severity_color};">[{issue.severity}]</span> '
                f'<span style="font-weight: bold; color: #FAFAFA;">Feature: {issue.column}</span> — Metric Frame: {issue.metric}<br>'
                f'<span style="color: #A0A5B5; font-size: 0.9em;">{issue.description} (Est. Scoring Impact: -{issue.score_impact})</span>'
                f'</div>'
            )
            st.markdown(markdown_block, unsafe_allow_html=True)
    except Exception as e:
        raise DashboardRenderingError(f"Failed to compile dynamic audit summary issue tracks panels: {e}")
