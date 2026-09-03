# ui/charts.py

from pathlib import Path
from typing import Any, TypedDict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import tomllib


class UIChartsConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float


class UIChartsConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int


class UIChartsAppConfig(TypedDict):
    scoring: UIChartsConfigScoring
    detection: UIChartsConfigDetection


class UIChartsException(Exception):
    pass


class UIChartsConfigLoadError(UIChartsException):
    pass


class ChartRenderingError(UIChartsException):
    pass


def load_ui_charts_config() -> UIChartsAppConfig:
    try:
        config_path = Path(__file__).resolve().parents[2] / "config.toml"
        with open(config_path, "rb") as f:
            return tomllib.load(f)  # type: ignore
    except FileNotFoundError as e:
        raise UIChartsConfigLoadError(f"Configuration file mapping missing: {e}")
    except tomllib.TOMLDecodeError as e:
        raise UIChartsConfigLoadError(f"Malformed configuration syntax execution: {e}")


_CONFIG: UIChartsAppConfig = load_ui_charts_config()
_DEFAULT_IQR_MULT: float = _CONFIG["detection"]["outlier_iqr_multiplier"]

_THEME: dict[str, Any] = {
    "font": {"family": "Inter, sans-serif", "color": "#FAFAFA"},
    "paper_bgcolor": "#0E1117",
    "plot_bgcolor": "#161A24",
    "colorway": ["#7F77DD", "#2ECC71", "#3498DB", "#F1C40F", "#E67E22", "#E74C3C"],
    "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
}


def render_distribution_histogram(df: pd.DataFrame, column: str) -> None:
    try:
        col_series = df[column]
        if not pd.api.types.is_numeric_dtype(col_series):
            st.warning(f"Column '{column}' is non-numeric. Aborting distribution visualization mapping.")
            return

        clean_series = col_series.dropna()
        if clean_series.empty:
            st.warning(f"Column '{column}' contains no numerical data parameters to map profiles.")
            return

        iqr_mult = float(st.session_state.get("outlier_iqr_multiplier", _DEFAULT_IQR_MULT))

        q25, q75 = np.percentile(clean_series, [25, 75], method="nearest")
        iqr = q75 - q25
        lower_fence = float(q25 - (iqr_mult * iqr))
        upper_fence = float(q75 + (iqr_mult * iqr))

        fig = px.histogram(
            df,
            x=column,
            nbins=40,
            color_discrete_sequence=[_THEME["colorway"][0]],
            title=f"Distribution Profile & Outlier Shading: {column}",
        )

        fig.update_layout(
            font=_THEME["font"],
            paper_bgcolor=_THEME["paper_bgcolor"],
            plot_bgcolor=_THEME["plot_bgcolor"],
            margin=_THEME["margin"],
            hovermode="x unified",
            bargap=0.05,
        )

        fig.update_traces(hovertemplate="Value Range: %{x}<br>Frequency Count: %{y}<extra></extra>")

        fig.add_vrect(
            x0=float(clean_series.min()),
            x1=float(lower_fence),
            fillcolor="#E74C3C",
            opacity=0.2,
            layer="below",
            line_width=0,
            annotation_text="Lower Outliers" if float(clean_series.min()) < float(lower_fence) else "",
        )

        fig.add_vrect(
            x0=float(upper_fence),
            x1=float(clean_series.max()),
            fillcolor="#E74C3C",
            opacity=0.2,
            layer="below",
            line_width=0,
            annotation_text="Upper Outliers" if float(clean_series.max()) > float(upper_fence) else "",
        )

        st.plotly_chart(fig, width="stretch")
    except KeyError as e:
        raise ChartRenderingError(f"Target distribution feature dimension index missing: {e}")
    except Exception as e:
        raise ChartRenderingError(f"Failure generating population variance distribution layout: {e}")


def render_missing_heatmap(df: pd.DataFrame) -> None:
    try:
        if df.empty:
            st.warning("Empty matrix frame state. Aborting missingness density charting mappings.")
            return

        missing_matrix = df.isna().astype(int).values
        col_names = list(df.columns)

        fig = go.Figure(data=go.Heatmap(
            z=missing_matrix,
            x=col_names,
            y=list(range(len(df))),
            colorscale=[[0, "#161A24"], [1, "#E74C3C"]],
            showscale=False,
            hovertemplate="Row: %{y}<br>Column: %{x}<br>Status: %{z}<extra></extra>",
        ))

        fig.update_layout(
            title="Row-Level Data Missingness Topology Matrix (Red = Missing)",
            font=_THEME["font"],
            paper_bgcolor=_THEME["paper_bgcolor"],
            plot_bgcolor=_THEME["plot_bgcolor"],
            margin=_THEME["margin"],
            xaxis={"tickangle": -45},
        )

        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        raise ChartRenderingError(f"Failure assembling missing trace heat density mapping: {e}")


def render_duplicate_scatter(df: pd.DataFrame, dup_indices: list[int]) -> None:
    try:
        if len(df.columns) < 2:
            st.warning("Insufficient dimensional metrics array scale (needs >= 2 columns) to generate scatter projection context.")
            return

        x_col = str(df.columns[0])
        y_col = str(df.columns[1])

        working_df = df.copy()
        working_df["Is_Duplicate"] = "Normal Record"

        valid_dup_indices = [idx for idx in dup_indices if idx in working_df.index]
        working_df.loc[valid_dup_indices, "Is_Duplicate"] = "Duplicate Footprint"

        fig = px.scatter(
            working_df,
            x=x_col,
            y=y_col,
            color="Is_Duplicate",
            color_discrete_map={"Normal Record": "#3498DB", "Duplicate Footprint": "#E74C3C"},
            title=f"Data Record Integrity Space Mapping ({x_col} vs {y_col})",
        )

        fig.update_layout(
            font=_THEME["font"],
            paper_bgcolor=_THEME["paper_bgcolor"],
            plot_bgcolor=_THEME["plot_bgcolor"],
            margin=_THEME["margin"],
            legend_title_text="Audit Category",
        )

        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        raise ChartRenderingError(f"Failure projecting multidimensional row duplicity coordinates: {e}")


def render_score_bar_chart(column_scores: dict[str, int]) -> None:
    try:
        if not column_scores:
            st.warning("Zero column tracking parameter matrices available to compile audit scorecard graph.")
            return

        sorted_scores = sorted(column_scores.items(), key=lambda x: x[1])
        cols = [item[0] for item in sorted_scores]
        scores = [item[1] for item in sorted_scores]

        colors: list[str] = []
        for s in scores:
            if s >= 90: colors.append("#2ECC71")
            elif s >= 70: colors.append("#3498DB")
            elif s >= 50: colors.append("#F1C40F")
            elif s >= 30: colors.append("#E67E22")
            else: colors.append("#E74C3C")

        fig = go.Figure(go.Bar(
            x=scores,
            y=cols,
            orientation="h",
            marker_color=colors,
            hovertemplate="Column: %{y}<br>Quality Index Score: %{x}/100<extra></extra>",
        ))

        fig.update_layout(
            title="Granular Summary Quality Index Matrix Breakdown per Feature Axis",
            font=_THEME["font"],
            paper_bgcolor=_THEME["paper_bgcolor"],
            plot_bgcolor=_THEME["plot_bgcolor"],
            margin=_THEME["margin"],
            xaxis={"range": [0, 105], "title": "Calculated Structural Index Metrics Baseline"},
        )

        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        raise ChartRenderingError(f"Failure rendering dimensional data metrics bar breakdown: {e}")
