# ui/sidebar.py

from pathlib import Path
from typing import TypedDict

import pandas as pd
import polars as pl
import streamlit as st
import tomllib

# ---------------------------------------------------------------------------
# Config TypedDicts
# ---------------------------------------------------------------------------

class UISidebarConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float


class UISidebarConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int


class UISidebarAppConfig(TypedDict):
    scoring: UISidebarConfigScoring
    detection: UISidebarConfigDetection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class UISidebarException(Exception):
    pass


class UISidebarConfigLoadError(UISidebarException):
    pass


class DataLoadError(UISidebarException):
    pass


class SidebarRenderingError(UISidebarException):
    pass


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_ui_sidebar_config() -> UISidebarAppConfig:
    try:
        config_path = Path(__file__).resolve().parents[2] / "config.toml"
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
        raise UISidebarConfigLoadError(f"Malformed schema array mapping inside target script: {e}")


_CONFIG: UISidebarAppConfig = load_ui_sidebar_config()
_MAX_SIZE_MB: int   = _CONFIG["detection"]["max_upload_mb"]
_DEFAULT_IQR: float = _CONFIG["detection"]["outlier_iqr_multiplier"]


# ---------------------------------------------------------------------------
# load_sample_dataset
# ---------------------------------------------------------------------------

@st.cache_data
def load_sample_dataset() -> pd.DataFrame:
    try:
        sample_path = Path(__file__).resolve().parents[2] / "data" / "sample_messy.csv"
        if not sample_path.exists():
            raise FileNotFoundError(f"Bundled sample dataset missing at: {sample_path}")
        return pl.read_csv(sample_path, infer_schema_length=10000, try_parse_dates=True).to_pandas()
    except FileNotFoundError as e:
        raise DataLoadError(f"Data layer file reference broken: {e}")
    except Exception as e:
        raise DataLoadError(f"Unexpected file read error: {e}")


# ---------------------------------------------------------------------------
# render_sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> pd.DataFrame | None:
    try:
        st.sidebar.title("Data Quality Auditor")
        st.sidebar.markdown("---")

        st.sidebar.subheader("Dataset Ingestion Panel")
        upload_mode = st.sidebar.radio(
            "Select Data Stream Pipeline Source",
            options=["User File Upload", "Load Bundled Sample Dataset"],
            key="data_stream_ingestion_selection",
        )

        active_df: pd.DataFrame | None = None

        if upload_mode == "User File Upload":
            uploaded_file = st.sidebar.file_uploader(
                "Drop Source CSV File",
                type=["csv"],
                help=f"Max upload size: {_MAX_SIZE_MB} MB.",
                key="user_raw_csv_file_uploader",
            )
            if uploaded_file is not None:
                if uploaded_file.size > _MAX_SIZE_MB * 1024 * 1024:
                    st.sidebar.error(f"File size exceeds max allowed limit of {_MAX_SIZE_MB} MB.")
                else:
                    try:
                        active_df = pl.read_csv(
                            uploaded_file,
                            infer_schema_length=10000,
                            try_parse_dates=True,
                        ).to_pandas()
                    except Exception as e:
                        st.sidebar.error(f"Failed to parse uploaded CSV: {e}")
        else:
            if st.sidebar.button(
                "Load Sample Dataset",
                key="trigger_sample_load_button",
            ):
                try:
                    active_df = load_sample_dataset()
                    st.sidebar.success("Sample dataset loaded successfully.")
                except DataLoadError as e:
                    st.sidebar.error(f"Sample load failed: {e}")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Analytical Audit Threshold Parameters")

        iqr_sensitivity = st.sidebar.slider(
            "Outlier Sensitivity (IQR Multiplier)",
            min_value=1.0,
            max_value=3.0,
            value=float(_DEFAULT_IQR),
            step=0.1,
            key="runtime_iqr_multiplier_coefficient",
        )
        st.session_state["outlier_iqr_multiplier"] = iqr_sensitivity

        dedup_scope = st.sidebar.multiselect(
            "Duplicate Check Columns (leave empty = full row)",
            options=(
                list(active_df.columns)
                if active_df is not None
                else ["Ingest a dataset to populate columns"]
            ),
            default=None,
            help="Select columns for targeted deduplication. If none selected, full rows are compared.",
            key="runtime_deduplication_tracking_subset_keys",
        )
        st.session_state["deduplication_subset_keys"] = [
            k for k in dedup_scope
            if active_df is not None and k in active_df.columns
        ]

        return active_df

    except Exception as e:
        raise SidebarRenderingError(f"Sidebar rendering failure: {e}")
