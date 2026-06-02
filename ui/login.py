import streamlit as st
from credentials import validate_credentials


def _inject_login_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* ── Dark neon background ── */
        .stApp {
            background: radial-gradient(ellipse at 20% 50%, rgba(0,255,255,0.04) 0%, transparent 60%),
                        radial-gradient(ellipse at 80% 20%, rgba(0,200,255,0.05) 0%, transparent 50%),
                        linear-gradient(160deg, #070B14 0%, #0A0E1A 40%, #0D1220 100%) !important;
        }

        /* ── Hide Streamlit chrome ── */
        #MainMenu, footer, header { visibility: hidden !important; }
        .block-container { padding-top: 0 !important; }

        /* ── Glassmorphism login card ── */
        .login-glass-card {
            background: rgba(13, 18, 32, 0.55) !important;
            border: 1px solid rgba(0, 255, 255, 0.18) !important;
            border-radius: 20px;
            padding: 52px 44px 44px 44px;
            backdrop-filter: blur(24px) saturate(180%);
            -webkit-backdrop-filter: blur(24px) saturate(180%);
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.5),
                0 0 0 1px rgba(0,255,255,0.06) inset,
                0 0 60px rgba(0, 255, 255, 0.05);
        }

        /* ── Logo / title area ── */
        .login-icon {
            font-size: 48px;
            text-align: center;
            margin-bottom: 10px;
            filter: drop-shadow(0 0 12px rgba(0,255,255,0.6));
        }
        .login-title {
            text-align: center;
            color: #00FFFF !important;
            font-size: 30px;
            font-weight: 700;
            letter-spacing: 6px;
            text-shadow: 0 0 24px rgba(0,255,255,0.5), 0 0 48px rgba(0,255,255,0.2);
            margin-bottom: 6px;
        }
        .login-subtitle {
            text-align: center;
            color: rgba(224, 247, 250, 0.4) !important;
            font-size: 11px;
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-bottom: 44px;
        }

        /* ── Divider line ── */
        .login-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0,255,255,0.3), transparent);
            margin-bottom: 36px;
        }

        /* ── Input fields ── */
        .stTextInput input {
            background: rgba(10, 14, 26, 0.7) !important;
            border: 1px solid rgba(0, 255, 255, 0.25) !important;
            border-radius: 8px !important;
            color: #E0F7FA !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 14px !important;
            padding: 14px 16px !important;
            transition: all 0.3s ease !important;
            backdrop-filter: blur(8px);
        }
        .stTextInput input:focus {
            border-color: #00FFFF !important;
            box-shadow: 0 0 0 3px rgba(0,255,255,0.12), 0 0 20px rgba(0,255,255,0.15) !important;
            background: rgba(0, 255, 255, 0.04) !important;
        }
        .stTextInput input::placeholder {
            color: rgba(224, 247, 250, 0.25) !important;
        }
        .stTextInput label {
            color: rgba(0, 255, 255, 0.65) !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 3px;
            text-transform: uppercase;
        }

        /* ── Auth button ── */
        .stButton > button {
            width: 100% !important;
            background: linear-gradient(135deg, rgba(0,255,255,0.12), rgba(0,200,255,0.08)) !important;
            border: 1px solid rgba(0,255,255,0.5) !important;
            color: #00FFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            letter-spacing: 4px;
            text-transform: uppercase;
            padding: 15px 24px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            backdrop-filter: blur(8px);
            margin-top: 8px !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, rgba(0,255,255,0.22), rgba(0,200,255,0.16)) !important;
            box-shadow: 0 0 28px rgba(0,255,255,0.35), 0 4px 16px rgba(0,0,0,0.4) !important;
            transform: translateY(-2px) !important;
            border-color: #00FFFF !important;
        }
        .stButton > button:active {
            transform: translateY(0px) !important;
        }

        /* ── Error / success alerts ── */
        div[data-testid="stAlert"] {
            border-radius: 8px !important;
            backdrop-filter: blur(8px);
        }

        /* ── Footer ── */
        .login-footer {
            text-align: center;
            margin-top: 36px;
            font-size: 10px;
            color: rgba(0, 255, 255, 0.2) !important;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        /* ── Scanline animation overlay ── */
        @keyframes scanline {
            0%   { transform: translateY(-100%); }
            100% { transform: translateY(100vh); }
        }
        .scanline {
            position: fixed;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(0,255,255,0.08), transparent);
            animation: scanline 6s linear infinite;
            pointer-events: none;
            z-index: 9999;
        }
        </style>

        <div class="scanline"></div>
        """,
        unsafe_allow_html=True,
    )


def render_login_page() -> bool:
    _inject_login_css()

    st.markdown("<div style='padding-top: 60px;'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])

    with col:
        # Glass card wrapper — top section (decorative)
        st.markdown(
            """
            <div class="login-glass-card">
                <div class="login-icon">🔐</div>
                <div class="login-title">AUDITOR</div>
                <div class="login-subtitle">Secure Access Portal — Enterprise Edition</div>
                <div class="login-divider"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Streamlit form (must be outside raw HTML)
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="Enter username",
                key="login_username_field",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
                key="login_password_field",
            )
            submitted = st.form_submit_button("🚀  AUTHENTICATE", type="primary")

            if submitted:
                is_valid, message = validate_credentials(username, password)
                if is_valid:
                    st.session_state["authenticated"] = True
                    st.session_state["username"]      = username
                    st.session_state["user_name"]     = username.upper()
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"⛔  {message}")
                    return False

        st.markdown(
            """
            <div class="login-footer">
                © 2026 DATA QUALITY AUDITOR &nbsp;|&nbsp; All rights reserved
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False
