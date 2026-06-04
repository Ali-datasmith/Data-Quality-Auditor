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
        raise UIDashboardConfigLoadError(f"Malformed schema file parsing parameters: {e}")
    except Exception as e:
        raise UIDashboardConfigLoadError(f"Unexpected operational layout setup failure: {e}")


_CONFIG: UIDashboardAppConfig = load_ui_dashboard_config()

_THEME: Dict[str, Any] = {
    "font":         {"family": "JetBrains Mono, monospace", "color": "#FAFAFA"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor":  "rgba(13,18,32,0.6)",
    "margin":        {"l": 30, "r": 30, "t": 40, "b": 30},
}


# ---------------------------------------------------------------------------
# render_overview_metrics
# FIX: shortened all 4 metric labels so they never truncate with "..."
#      Old → New:
#      "Overall Quality Index"      → "Quality Score"
#      "Total Logged Rows"          → "Total Rows"
#      "Total Feature Columns"      → "Columns"
#      "Detected Issue Indicators"  → "Issues Found"
# ---------------------------------------------------------------------------

def render_overview_metrics(
    score: int,
    profile: Dict[str, Dict[str, Any]],
    issues: List[QualityIssue],
) -> None:
    try:
        if not profile:
            return

        first_col   = next(iter(profile.values()))
        total_rows  = int(first_col.get("total_rows", 0))
        total_cols  = len(profile)
        issue_count = len(issues)
        label_meta  = get_score_label(score)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                label="Quality Score",        # was: "Overall Quality Index"
                value=f"{score}/100",
                delta=label_meta.category,
            )
        with c2:
            st.metric(
                label="Total Rows",           # was: "Total Logged Rows"
                value=f"{total_rows:,}",
            )
        with c3:
            st.metric(
                label="Columns",              # was: "Total Feature Columns"
                value=f"{total_cols}",
            )
        with c4:
            st.metric(
                label="Issues Found",         # was: "Detected Issue Indicators"
                value=f"{issue_count}",
                delta="Requires Fix" if issue_count > 0 else "Clean",
                delta_color="inverse" if issue_count > 0 else "normal",
            )

    except Exception as e:
        raise DashboardRenderingError(
            f"Failed to render core overview status metrics layout panels: {e}"
        )


def render_score_gauge(score: int) -> None:
    try:
        label_meta = get_score_label(score)

        # Enhanced gauge with vibrant gradient bar and glassmorphic styling
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            number={
                "font": {"size": 56, "color": "#00FFFF", "family": "JetBrains Mono"},
                "suffix": "",
                "valueformat": ".0f",
            },
            delta={
                "reference": 75,
                "increasing": {"color": "#2ECC71"},
                "decreasing": {"color": "#E74C3C"},
                "font": {"size": 14, "color": "#E0F7FA"},
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 2,
                    "tickcolor": "#00FFFF",
                    "tickfont": {"size": 12, "color": "rgba(0,255,255,0.7)", "family": "JetBrains Mono"},
                    "ticklen": 8,
                },
                "bar": {
                    "color": label_meta.color_hex,
                    "thickness": 0.25,
                    "line": {
                        "color": label_meta.color_hex,
                        "width": 3,
                    }
                },
                "bgcolor": "rgba(255,255,255,0.02)",
                "borderwidth": 2,
                "bordercolor": "rgba(0,255,255,0.15)",
                "steps": [
                    {"range": [0,  30],  "color": "rgba(231, 76, 60, 0.15)", "name": "Critical"},
                    {"range": [30, 50],  "color": "rgba(230, 126, 34, 0.15)", "name": "Poor"},
                    {"range": [50, 70],  "color": "rgba(241, 196, 15, 0.15)", "name": "Fair"},
                    {"range": [70, 90],  "color": "rgba(52, 152, 218, 0.15)", "name": "Good"},
                    {"range": [90, 100], "color": "rgba(46, 204, 113, 0.15)", "name": "Excellent"},
                ],
                "threshold": {
                    "line": {"color": "rgba(0,255,255,0.3)", "width": 2},
                    "thickness": 0.75,
                    "value": 85,
                }
            },
        ))

        fig.update_layout(
            font={
                "family": "JetBrains Mono, monospace",
                "color": "#FAFAFA",
                "size": 12,
            },
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
            height=300,
            showlegend=False,
            annotations=[
                dict(
                    text=f"<b>{label_meta.category}</b>",
                    x=0.5,
                    y=-0.15,
                    showarrow=False,
                    font=dict(size=16, color=label_meta.color_hex, family="JetBrains Mono"),
                    xref="paper",
                    yref="paper",
                )
            ],
        )

        # Add custom styling to make it pop
        fig.update_traces(
            selector=dict(type="indicator"),
            hoverlabel=dict(
                bgcolor="rgba(13,18,32,0.9)",
                bordercolor="#00FFFF",
                font=dict(size=13, color="#00FFFF", family="JetBrains Mono"),
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={"responsive": True, "displayModeBar": False})

    except Exception as e:
        raise DashboardRenderingError(
            f"Failed to generate dial gauge mapping visualization parameters: {e}"
        )


def render_column_table(
    profile: Dict[str, Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    try:
        table_records: List[Dict[str, Any]] = []

        for col_name, stats in profile.items():
            col_score    = scores.get(col_name, 0)
            missing_cnt  = int(stats.get("missing_count", 0))
            outlier_cnt  = int(stats.get("outlier_count", 0))
            mismatch_cnt = int(stats.get("mismatch_count", 0))

            badges: List[str] = []
            if missing_cnt  > 0: badges.append("🚨 Missing")
            if outlier_cnt  > 0: badges.append("📊 Outliers")
            if mismatch_cnt > 0: badges.append("⚠️ Mismatch")
            if not badges:       badges.append("✅ Clean")

            table_records.append({
                "Column":        col_name,
                "Type":          str(stats.get("dtype", "Unknown")),
                "Score":         col_score,
                "Missing":       missing_cnt,
                "Outliers":      outlier_cnt,
                "Status":        ", ".join(badges),
            })

        summary_df = pd.DataFrame(table_records).sort_values(
            by="Score", ascending=True
        )

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score",
                    help="Column quality score (0–100)",
                    format="%d",
                    min_value=0,
                    max_value=100,
                )
            },
        )

    except Exception as e:
        raise DashboardRenderingError(
            f"Failed to generate data matrix summary tracking grids: {e}"
        )


def render_issue_list(issues: List[QualityIssue]) -> None:
    try:
        st.markdown("### Detected Issues")

        if not issues:
            st.success("No issues detected. Dataset is clean.")
            return

        for issue in issues:
            severity_color = (
                "#E74C3C" if issue.severity == "Critical"
                else "#E67E22" if issue.severity == "High"
                else "#F1C40F"
            )

            st.markdown(
                f'<div style="border-left:4px solid {severity_color}; '
                f'padding-left:15px; margin-bottom:12px;">'
                f'<span style="font-weight:bold; color:{severity_color};">'
                f'[{issue.severity}]</span> '
                f'<span style="font-weight:bold; color:#FAFAFA;">'
                f'{issue.column}</span> — {issue.metric}<br>'
                f'<span style="color:#A0A5B5; font-size:0.9em;">'
                f'{issue.description} '
                f'(Score impact: -{issue.score_impact})</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    except Exception as e:
        raise DashboardRenderingError(
            f"Failed to compile dynamic audit summary issue tracks panels: {e}"
        )
