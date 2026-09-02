# app.py

import tomllib
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Imports — cleaned: each module imported exactly once with the full set
# ---------------------------------------------------------------------------
from core.profiler import (
    generate_profile,
    detect_duplicates,
    detect_outliers,
    run_duckdb_anomalies,
)
from core.scorer import (
    score_column,
    score_dataframe,
    generate_issue_summary,
)
from ui.sidebar import render_sidebar
from ui.dashboard import (
    render_overview_metrics,
    render_score_gauge,
    render_column_table,
    render_issue_list,
)
from ui.report_card import render_column_card, render_suggestion_box
from ui.login import render_login_page
from utils.cleaner import (
    suggest_fixes,
    apply_fixes,
    export_cleaned_csv,
    generate_change_log,
)


# ---------------------------------------------------------------------------
# Config TypedDicts
# ---------------------------------------------------------------------------

class AppConfigScoring(TypedDict):
    completeness_weight: float
    uniqueness_weight: float
    consistency_weight: float
    outlier_weight: float


class AppConfigDetection(TypedDict):
    outlier_iqr_multiplier: float
    max_upload_mb: int


class AppConfig(TypedDict):
    scoring: AppConfigScoring
    detection: AppConfigDetection


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AppConfigLoadError(Exception):
    pass


class OrchestrationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_app_config() -> AppConfig:
    try:
        config_path = Path(__file__).resolve().parent / "config.toml"
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
        raise AppConfigLoadError(f"Malformed TOML configuration syntax: {e}")


_CONFIG: AppConfig = load_app_config()


# ---------------------------------------------------------------------------
# Session state initialiser
# ---------------------------------------------------------------------------

def initialize_session_state() -> None:
    try:
        defaults: dict[str, Any] = {
            "authenticated": False,
            "username":      None,
            "user_name":     None,
            "raw_df":        None,
            "cleaned_df":    None,
            "selected_fixes": [],
            "profile":       None,
            "col_scores":    None,
            "overall_score": None,
            "issues":        None,
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
    except Exception as e:
        raise OrchestrationError(f"Session state initialization failure: {e}")


# ---------------------------------------------------------------------------
# Profile enrichment — merges profiler + outlier + anomaly + duplicate data
# into a single flat dict per column that scorer and cleaner both consume
# ---------------------------------------------------------------------------

def _build_enriched_profile(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    try:
        raw_profile    = generate_profile(df)
        anomaly_report = run_duckdb_anomalies(df)
        dup_report     = detect_duplicates(df)
        total_rows     = len(df)

        enriched: dict[str, dict[str, Any]] = {}
        for col_name, col_profile in raw_profile.items():
            outlier_report = detect_outliers(df, col_name)
            mismatch_count = sum(
                1 for m in anomaly_report.type_mismatches
                if m.get("column") == col_name
            )
            enriched[col_name] = {
                "dtype":              col_profile.dtype,
                "missing_count":      col_profile.missing_count,
                "missing_percentage": col_profile.missing_percentage,
                "unique_count":       col_profile.unique_count,
                "min_value":          col_profile.min_value,
                "max_value":          col_profile.max_value,
                "mean_value":         col_profile.mean_value,
                "std_value":          col_profile.std_value,
                "top_values":         col_profile.top_values,
                "outlier_count":      outlier_report.count,
                "outlier_indices":    outlier_report.indices,
                "lower_fence":        outlier_report.lower_fence,
                "upper_fence":        outlier_report.upper_fence,
                "mismatch_count":     mismatch_count,
                "duplicate_count":    dup_report.count,
                "total_rows":         total_rows,
            }
        return enriched
    except Exception as e:
        raise OrchestrationError(f"Profile enrichment pipeline failure: {e}")


def _build_column_scores(profile: dict[str, dict[str, Any]]) -> dict[str, int]:
    try:
        return {col_name: score_column(stats) for col_name, stats in profile.items()}
    except Exception as e:
        raise OrchestrationError(f"Column score computation failure: {e}")


# ---------------------------------------------------------------------------
# CSS injection — neon dark theme
# ---------------------------------------------------------------------------

def _inject_neon_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* ── Master background — rich midnight with vivid glow orbs ── */
        .stApp {
            background:
                radial-gradient(ellipse at 8%  30%, rgba(0,255,255,0.13)  0%, transparent 45%),
                radial-gradient(ellipse at 92% 10%, rgba(80,0,255,0.18)   0%, transparent 40%),
                radial-gradient(ellipse at 50% 85%, rgba(0,120,255,0.14)  0%, transparent 45%),
                radial-gradient(ellipse at 75% 55%, rgba(120,0,255,0.10)  0%, transparent 40%),
                radial-gradient(ellipse at 25% 70%, rgba(0,200,255,0.09)  0%, transparent 38%),
                linear-gradient(145deg, #0D0D1F 0%, #111228 35%, #0E1530 65%, #0A1525 100%) !important;
        }

        /* ── Sidebar — vivid glass over richer bg ── */
        section[data-testid="stSidebar"] {
            background: rgba(14, 18, 38, 0.55) !important;
            backdrop-filter: blur(28px) saturate(180%) brightness(1.1) !important;
            -webkit-backdrop-filter: blur(28px) saturate(180%) brightness(1.1) !important;
            border-right: 1px solid rgba(0, 255, 255, 0.15) !important;
            box-shadow: 4px 0 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(80,0,255,0.06) inset !important;
        }

        /* ── Typography ── */
        h1, h2, h3, h4, h5, h6 {
            color: #00FFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            text-shadow: 0 0 16px rgba(0, 255, 255, 0.35), 0 0 32px rgba(0,255,255,0.1);
            letter-spacing: 2px;
        }
        p, label, span, div {
            color: #E0F7FA !important;
        }

        /* ── Master metric containers ── */
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(0, 255, 255, 0.22) !important;
            border-radius: 14px !important;
            padding: 20px !important;
            backdrop-filter: blur(20px) saturate(200%) brightness(1.15) !important;
            -webkit-backdrop-filter: blur(20px) saturate(200%) brightness(1.15) !important;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.45),
                0 0 0 1px rgba(255, 255, 255, 0.05) inset,
                0 1px 0 rgba(255,255,255,0.08) inset,
                0 0 28px rgba(0, 255, 255, 0.06) !important;
            transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px) !important;
            box-shadow:
                0 12px 40px rgba(0, 0, 0, 0.55),
                0 0 0 1px rgba(0, 255, 255, 0.15) inset,
                0 0 36px rgba(0, 255, 255, 0.12) !important;
        }
        [data-testid="stMetricLabel"] {
            color: rgba(0, 255, 255, 0.65) !important;
            font-size: 10px !important;
            letter-spacing: 3px !important;
            text-transform: uppercase !important;
        }
        [data-testid="stMetricValue"] {
            color: #00FFFF !important;
            font-size: 30px !important;
            font-weight: 700 !important;
            text-shadow: 0 0 12px rgba(0, 255, 255, 0.5) !important;
        }
        [data-testid="stMetricDelta"] {
            color: rgba(0, 255, 255, 0.55) !important;
            font-size: 11px !important;
        }

        /* ── Buttons — glass neon ── */
        .stButton > button {
            background: linear-gradient(135deg, rgba(0,255,255,0.08), rgba(0,180,255,0.05)) !important;
            border: 1px solid rgba(0, 255, 255, 0.4) !important;
            color: #00FFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 12px !important;
            letter-spacing: 3px !important;
            text-transform: uppercase !important;
            border-radius: 8px !important;
            backdrop-filter: blur(8px) !important;
            transition: all 0.25s ease !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, rgba(0,255,255,0.18), rgba(0,180,255,0.12)) !important;
            box-shadow: 0 0 24px rgba(0, 255, 255, 0.3), 0 4px 16px rgba(0,0,0,0.4) !important;
            transform: translateY(-2px) !important;
            border-color: #00FFFF !important;
        }
        .stButton > button:active {
            transform: translateY(0px) !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, rgba(0,255,255,0.15), rgba(0,200,255,0.1)) !important;
            border-color: #00FFFF !important;
            box-shadow: 0 0 16px rgba(0, 255, 255, 0.25) !important;
        }

        /* ── File uploader ── */
        [data-testid="stFileUploader"] {
            background: rgba(13, 18, 32, 0.5) !important;
            border: 1px dashed rgba(0, 255, 255, 0.3) !important;
            border-radius: 10px !important;
            backdrop-filter: blur(8px) !important;
        }

        /* ── DataFrame ── */
        .stDataFrame, [data-testid="stDataFrame"] {
            background: rgba(10, 14, 26, 0.6) !important;
            border: 1px solid rgba(0, 255, 255, 0.15) !important;
            border-radius: 10px !important;
            backdrop-filter: blur(12px) !important;
            overflow: hidden;
        }

        /* ── Expander — vivid glass card ── */
        .stExpander {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(0, 255, 255, 0.18) !important;
            border-radius: 14px !important;
            backdrop-filter: blur(20px) saturate(180%) brightness(1.1) !important;
            -webkit-backdrop-filter: blur(20px) saturate(180%) brightness(1.1) !important;
            box-shadow:
                0 4px 24px rgba(0,0,0,0.4),
                0 0 0 1px rgba(255,255,255,0.05) inset,
                0 1px 0 rgba(255,255,255,0.06) inset !important;
        }
        .stExpander summary {
            color: #00FFFF !important;
            letter-spacing: 1px !important;
        }
        .stExpander summary:hover {
            color: #80FFFF !important;
        }

        /* ── Text inputs ── */
        .stTextInput input, .stNumberInput input {
            background: rgba(10, 14, 26, 0.7) !important;
            border: 1px solid rgba(0, 255, 255, 0.25) !important;
            border-radius: 8px !important;
            color: #E0F7FA !important;
            font-family: 'JetBrains Mono', monospace !important;
            backdrop-filter: blur(8px) !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: #00FFFF !important;
            box-shadow: 0 0 0 3px rgba(0,255,255,0.1), 0 0 16px rgba(0,255,255,0.12) !important;
        }

        /* ── Selectbox ── */
        .stSelectbox div[data-baseweb="select"] > div {
            background: rgba(13, 18, 32, 0.7) !important;
            border-color: rgba(0, 255, 255, 0.25) !important;
            border-radius: 8px !important;
            backdrop-filter: blur(8px) !important;
        }

        /* ── Multiselect ── */
        .stMultiSelect div[data-baseweb="select"] > div {
            background: rgba(13, 18, 32, 0.7) !important;
            border-color: rgba(0, 255, 255, 0.25) !important;
            border-radius: 8px !important;
        }

        /* ── Slider ── */
        [data-testid="stSlider"] > div > div > div {
            background: rgba(0, 255, 255, 0.3) !important;
        }
        [data-testid="stSlider"] > div > div > div > div {
            background: #00FFFF !important;
            box-shadow: 0 0 8px rgba(0,255,255,0.6) !important;
        }

        /* ── Radio buttons ── */
        [data-testid="stRadio"] label {
            color: #E0F7FA !important;
        }

        /* ── Dividers ── */
        hr {
            border-color: rgba(0, 255, 255, 0.12) !important;
        }

        /* ── Download button ── */
        [data-testid="stDownloadButton"] > button {
            background: linear-gradient(135deg, rgba(0,255,255,0.1), rgba(0,180,255,0.07)) !important;
            border-color: rgba(0, 255, 255, 0.45) !important;
            color: #00FFFF !important;
            border-radius: 8px !important;
            backdrop-filter: blur(8px) !important;
        }
        [data-testid="stDownloadButton"] > button:hover {
            box-shadow: 0 0 20px rgba(0,255,255,0.3) !important;
            transform: translateY(-1px) !important;
        }

        /* ── Alert / info boxes ── */
        div[data-testid="stAlert"] {
            background: rgba(13, 18, 32, 0.6) !important;
            border-left-color: #00FFFF !important;
            border-radius: 8px !important;
            backdrop-filter: blur(12px) !important;
        }

        /* ── Spinner ── */
        .stSpinner > div {
            border-top-color: #00FFFF !important;
        }

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(10, 14, 26, 0.5) !important;
            border-radius: 8px !important;
            backdrop-filter: blur(8px) !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: rgba(0,255,255,0.6) !important;
            letter-spacing: 2px !important;
        }
        .stTabs [aria-selected="true"] {
            color: #00FFFF !important;
            border-bottom-color: #00FFFF !important;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(10,14,26,0.5); }
        ::-webkit-scrollbar-thumb {
            background: rgba(0,255,255,0.3);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(0,255,255,0.5);
        }

        /* ── Scanline animation ── */
        @keyframes scanline {
            0%   { transform: translateY(-100%); }
            100% { transform: translateY(100vh); }
        }
        .scanline {
            position: fixed;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(0,255,255,0.06), transparent);
            animation: scanline 8s linear infinite;
            pointer-events: none;
            z-index: 9999;
        }
        </style>
        <div class="scanline"></div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Landing page (shown when no dataset is loaded)
# ---------------------------------------------------------------------------

def _render_landing() -> None:
    st.markdown(
        """
        <div style="
            text-align: center;
            padding: 80px 40px;
            border: 1px solid rgba(0,255,255,0.15);
            border-radius: 12px;
            background: rgba(0,255,255,0.02);
            margin-top: 40px;
        ">
            <h1 style="font-size: 48px; letter-spacing: 6px;">DATA QUALITY AUDITOR</h1>
            <p style="color: rgba(0,255,255,0.6) !important; font-size: 14px; letter-spacing: 3px; margin-top: 12px;">
                UPLOAD ANY CSV — GET A FULL QUALITY SCORE IN 10 SECONDS
            </p>
            <div style="margin-top: 40px; display: flex; justify-content: center; gap: 40px; flex-wrap: wrap;">
                <div style="border: 1px solid rgba(0,255,255,0.2); padding: 20px 30px; border-radius: 8px; min-width: 160px;">
                    <div style="color: #00FFFF !important; font-size: 24px; font-weight: 700;">0–100</div>
                    <div style="color: rgba(0,255,255,0.5) !important; font-size: 11px; letter-spacing: 2px; margin-top: 6px;">QUALITY SCORE</div>
                </div>
                <div style="border: 1px solid rgba(0,255,255,0.2); padding: 20px 30px; border-radius: 8px; min-width: 160px;">
                    <div style="color: #00FFFF !important; font-size: 24px; font-weight: 700;">IQR</div>
                    <div style="color: rgba(0,255,255,0.5) !important; font-size: 11px; letter-spacing: 2px; margin-top: 6px;">OUTLIER DETECTION</div>
                </div>
                <div style="border: 1px solid rgba(0,255,255,0.2); padding: 20px 30px; border-radius: 8px; min-width: 160px;">
                    <div style="color: #00FFFF !important; font-size: 24px; font-weight: 700;">AUTO</div>
                    <div style="color: rgba(0,255,255,0.5) !important; font-size: 11px; letter-spacing: 2px; margin-top: 6px;">CLEAN + EXPORT</div>
                </div>
            </div>
            <p style="color: rgba(0,255,255,0.35) !important; font-size: 12px; margin-top: 40px; letter-spacing: 1px;">
                ← USE THE SIDEBAR TO UPLOAD A FILE OR LOAD THE SAMPLE DATASET
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        st.set_page_config(
            page_title="Data Quality Auditor",
            page_icon="🛡️",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        initialize_session_state()

        # ===== AUTHENTICATION CHECK =====
        if not st.session_state.get("authenticated", False):
            render_login_page()
            return

        # ===== MAIN APP STARTS HERE =====
        _inject_neon_css()

        # ===== SIDEBAR USER INFO & LOGOUT =====
        with st.sidebar:
            username = st.session_state.get("username", "user")
            st.markdown(
                f"""
                <div style='
                    background: rgba(0,255,255,0.05);
                    border: 1px solid rgba(0,255,255,0.2);
                    border-radius: 6px;
                    padding: 12px;
                    margin-bottom: 12px;
                    font-size: 11px;
                    letter-spacing: 1px;
                '>
                    <span style='color: rgba(0,255,255,0.5);'>👤 LOGGED IN AS</span><br>
                    <span style='color: #00FFFF; font-weight: 700;'>{username.upper()}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚪 LOGOUT", key="logout_btn", use_container_width=True):
                st.session_state["authenticated"] = False
                st.session_state["username"]      = None
                st.session_state["user_name"]     = None
                st.rerun()
            st.markdown("---")

        df: pd.DataFrame | None = render_sidebar()

        # New file uploaded — reset all cached analysis so it re-runs cleanly
        if df is not None:
            st.session_state["raw_df"]        = df
            st.session_state["cleaned_df"]    = None
            st.session_state["profile"]       = None
            st.session_state["col_scores"]    = None
            st.session_state["overall_score"] = None
            st.session_state["issues"]        = None

        active_df: pd.DataFrame | None = st.session_state.get("raw_df")

        if active_df is None:
            st.info(
                "Awaiting data stream. Upload a CSV or load the bundled sample from the sidebar."
            )
            _render_landing()
            return

        st.markdown(
            "<h1 style='letter-spacing:6px;'>🛡 DATA QUALITY AUDITOR</h1>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Run analysis once and cache in session state
        if st.session_state.get("profile") is None:
            with st.spinner("SCANNING DATA MATRIX..."):
                prof = _build_enriched_profile(active_df)
                scores = _build_column_scores(prof)
                ov_score = score_dataframe(prof)
                iss = generate_issue_summary(prof)

                st.session_state["profile"]       = prof
                st.session_state["col_scores"]    = scores
                st.session_state["overall_score"] = ov_score
                st.session_state["issues"]        = iss

        profile: dict[str, dict[str, Any]] = st.session_state["profile"]
        col_scores: dict[str, int]         = st.session_state["col_scores"]
        overall_score: int                 = st.session_state["overall_score"]
        issues: list[Any]                  = st.session_state["issues"]

        dup_report = detect_duplicates(active_df)
        duplicate_count = dup_report.count

        # --- Dashboard ---
        render_overview_metrics(overall_score, profile, issues)
        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 2])
        with c1:
            render_score_gauge(overall_score)
        with c2:
            render_column_table(profile, col_scores)

        st.markdown("---")
        render_issue_list(issues)

        # --- Per-column deep-dive cards ---
        st.markdown("---")
        st.subheader("FEATURE AXIS DEEP-DIVE REPORTS")
        for col_name, stats in profile.items():
            c_score = col_scores.get(col_name, 0)
            render_column_card(col_name, stats, c_score, active_df)

        # --- Remediation pipeline ---
        st.markdown("---")
        st.subheader("REMEDIATION PIPELINE")

        all_suggestions = suggest_fixes(
            profile,
            duplicate_count=duplicate_count,
            source_df=active_df,
        )
        render_suggestion_box(all_suggestions)

        if st.button("EXECUTE ALL FIXES", type="primary", key="execute_fixes_btn"):
            with st.spinner("APPLYING REMEDIATIONS..."):
                cleaned = apply_fixes(active_df, [s.__dict__ for s in all_suggestions])
                st.session_state["cleaned_df"] = cleaned
                change_log = generate_change_log(active_df, cleaned)
                st.success(
                    f"COMPLETE — {change_log.rows_dropped} rows dropped, "
                    f"{sum(change_log.mutations_applied.values())} values mutated."
                )

        cleaned_df: pd.DataFrame | None = st.session_state.get("cleaned_df")
        if cleaned_df is not None:
            csv_bytes = export_cleaned_csv(cleaned_df)
            st.download_button(
                label="⬇ DOWNLOAD CLEANED CSV",
                data=csv_bytes,
                file_name="audited_cleaned_dataset.csv",
                mime="text/csv",
                type="primary",
                key="download_cleaned_csv_btn",
            )

    except AppConfigLoadError as e:
        st.error(f"CRITICAL INIT FAILURE: {e}")
    except OrchestrationError as e:
        st.error(f"ORCHESTRATION FAULT: {e}")
    except Exception as e:
        st.error(f"UNHANDLED EXCEPTION: {e}")


if __name__ == "__main__":
    main()
