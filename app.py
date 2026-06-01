import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

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
    get_score_label,
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
from credentials import get_user_name


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
    except Exception as e:
        raise AppConfigLoadError(f"Unexpected configuration load failure: {e}")


_CONFIG: AppConfig = load_app_config()


# ---------------------------------------------------------------------------
# Session state initialiser
# ---------------------------------------------------------------------------

def initialize_session_state() -> None:
    try:
        defaults: Dict[str, Any] = {
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

def _build_enriched_profile(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    try:
        raw_profile    = generate_profile(df)
        anomaly_report = run_duckdb_anomalies(df)
        dup_report     = detect_duplicates(df)
        total_rows     = len(df)

        enriched: Dict[str, Dict[str, Any]] = {}
        for col_name, col_profile in raw_profile.items():
            outlier_report = detect_outliers(df, col_name)
            mismatch_count = sum(
                1 for m in anomaly_report.type_mismatches
                if m.get("column") == col_name
            )
            enriched[col_name] = {
                "dtype":             col_profile.dtype,
                "missing_count":     col_profile.missing_count,
                "missing_percentage": col_profile.missing_percentage,
                "unique_count":      col_profile.unique_count,
                "min_value":         col_profile.min_value,
                "max_value":         col_profile.max_value,
                "mean_value":        col_profile.mean_value,
                "std_value":         col_profile.std_value,
                "top_values":        col_profile.top_values,
                "outlier_count":     outlier_report.count,
                "outlier_indices":   outlier_report.indices,
                "lower_fence":       outlier_report.lower_fence,
                "upper_fence":       outlier_report.upper_fence,
                "mismatch_count":    mismatch_count,
                # NEW — duplicate count wired into every column so scorer
                # can apply the duplicate penalty correctly
                "duplicate_count":   dup_report.count,
                "total_rows":        total_rows,
            }
        return enriched
    except Exception as e:
        raise OrchestrationError(f"Profile enrichment pipeline failure: {e}")


def _build_column_scores(profile: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
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
        .stApp {
            background-color: #0A0E1A !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #0D1220 !important;
            border-right: 1px solid rgba(0, 255, 255, 0.15) !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #00FFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            text-shadow: 0 0 12px rgba(0, 255, 255, 0.4);
            letter-spacing: 2px;
        }
        p, label, span, div {
            color: #E0F7FA !important;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(0,255,255,0.05), rgba(0,255,255,0.02));
            border: 1px solid rgba(0, 255, 255, 0.25);
            border-radius: 8px;
            padding: 16px !important;
        }
        [data-testid="stMetricLabel"] {
            color: rgba(0, 255, 255, 0.7) !important;
            font-size: 11px !important;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: #00FFFF !important;
            font-size: 28px !important;
            font-weight: 700 !important;
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }
        [data-testid="stMetricDelta"] {
            color: rgba(0, 255, 255, 0.6) !important;
            font-size: 11px !important;
        }
        .stButton > button {
            background: transparent !important;
            border: 1px solid #00FFFF !important;
            color: #00FFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            letter-spacing: 2px;
            text-transform: uppercase;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background: rgba(0, 255, 255, 0.1) !important;
            box-shadow: 0 0 16px rgba(0, 255, 255, 0.3);
        }
        .stButton > button[kind="primary"] {
            border-color: #00FFFF !important;
            box-shadow: 0 0 12px rgba(0, 255, 255, 0.2);
        }
        [data-testid="stFileUploader"] {
            border: 1px dashed rgba(0, 255, 255, 0.3) !important;
            border-radius: 8px;
            background: rgba(0, 255, 255, 0.02) !important;
        }
        .stDataFrame, [data-testid="stDataFrame"] {
            border: 1px solid rgba(0, 255, 255, 0.15) !important;
            border-radius: 8px;
        }
        .stExpander {
            border: 1px solid rgba(0, 255, 255, 0.2) !important;
            border-radius: 8px !important;
            background: rgba(0, 255, 255, 0.02) !important;
        }
        .stExpander summary {
            color: #00FFFF !important;
        }
        [data-testid="stRadio"] label {
            color: #E0F7FA !important;
        }
        [data-testid="stSlider"] {
            color: #00FFFF !important;
        }
        .stSelectbox div[data-baseweb="select"] > div {
            background-color: #0D1220 !important;
            border-color: rgba(0, 255, 255, 0.3) !important;
        }
        hr {
            border-color: rgba(0, 255, 255, 0.15) !important;
        }
        [data-testid="stDownloadButton"] > button {
            border-color: rgba(0, 255, 255, 0.5) !important;
            color: #00FFFF !important;
        }
        div[data-testid="stAlert"] {
            background: rgba(0, 255, 255, 0.05) !important;
            border-left-color: #00FFFF !important;
        }
        </style>
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
        # FIX: duplicate page_icon and duplicate initial_sidebar_state args removed
        st.set_page_config(
            page_title="Data Quality Auditor",
            page_icon="🛡️",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        initialize_session_state()

        # ===== AUTHENTICATION CHECK =====
        # Must happen BEFORE _inject_neon_css() and BEFORE main UI rendering
        if not st.session_state.get("authenticated", False):
            render_login_page()
            return  # Stop — don't render the main app until login succeeds

        # ===== MAIN APP STARTS HERE =====
        _inject_neon_css()

        df: Optional[pd.DataFrame] = render_sidebar()

        # New file uploaded — reset all cached analysis so it re-runs cleanly
        if df is not None:
            st.session_state["raw_df"]       = df
            # FIX: was reset twice (`cleaned_df = None` appeared on two consecutive
            # lines). Now each key is set exactly once.
            st.session_state["cleaned_df"]   = None
            st.session_state["profile"]      = None
            st.session_state["col_scores"]   = None
            st.session_state["overall_score"] = None
            st.session_state["issues"]       = None

        active_df: Optional[pd.DataFrame] = st.session_state.get("raw_df")

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

        # ===== SIDEBAR USER INFO & LOGOUT =====
        with st.sidebar:
            st.markdown("---")
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
                st.session_state["username"] = None
                st.session_state["user_name"] = None
                st.rerun()
            
            st.markdown("---")

        # Run analysis once and cache in session state
        if st.session_state.get("profile") is None:
            with st.spinner("SCANNING DATA MATRIX..."):
                profile      = _build_enriched_profile(active_df)
                col_scores   = _build_column_scores(profile)
                overall_score = score_dataframe(profile)
                issues       = generate_issue_summary(profile)

                st.session_state["profile"]       = profile
                st.session_state["col_scores"]    = col_scores
                st.session_state["overall_score"] = overall_score
                st.session_state["issues"]        = issues

        profile:       Dict[str, Dict[str, Any]] = st.session_state["profile"]
        col_scores:    Dict[str, int]            = st.session_state["col_scores"]
        overall_score: int                       = st.session_state["overall_score"]
        issues:        List[Any]                 = st.session_state["issues"]

        # Duplicate report (lightweight — not cached, uses session iqr pref)
        dup_report     = detect_duplicates(active_df)
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

        # FIX: two separate execute buttons existed (one from old code, one from new).
        # Merged into a single button with change log feedback.
        if st.button("EXECUTE ALL FIXES", type="primary", key="execute_fixes_btn"):
            with st.spinner("APPLYING REMEDIATIONS..."):
                cleaned = apply_fixes(active_df, [s.__dict__ for s in all_suggestions])
                st.session_state["cleaned_df"] = cleaned
                change_log = generate_change_log(active_df, cleaned)
                st.success(
                    f"COMPLETE — {change_log.rows_dropped} rows dropped, "
                    f"{sum(change_log.mutations_applied.values())} values mutated."
                )

        cleaned_df: Optional[pd.DataFrame] = st.session_state.get("cleaned_df")
        if cleaned_df is not None:
            csv_bytes = export_cleaned_csv(cleaned_df)
            # FIX: duplicate label and duplicate type= args removed
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
