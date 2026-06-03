import streamlit as st
from credentials import validate_credentials


def _inject_login_css() -> None:
    """Injects custom dark neon CSS styling and glassmorphism structure."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* ── Dark neon background ── */
        .stApp {
            background:
                radial-gradient(ellipse at 8%  30%, rgba(0,255,255,0.13)  0%, transparent 45%),
                radial-gradient(ellipse at 92% 10%, rgba(80,0,255,0.18)   0%, transparent 40%),
                radial-gradient(ellipse at 50% 85%, rgba(0,120,255,0.14)  0%, transparent 45%),
                radial-gradient(ellipse at 75% 55%, rgba(120,0,255,0.10)  0%, transparent 40%),
                radial-gradient(ellipse at 25% 70%, rgba(0,200,255,0.09)  0%, transparent 38%),
                linear-gradient(145deg, #0D0D1F 0%, #111228 35%, #0E1530 65%, #0A1525 100%) !important;
        }

        /* ── Hide Streamlit chrome ── */
        #MainMenu, footer, header { visibility: hidden !important; }
        .block-container { padding-top: 0 !important; }

        /* ── Native element alignment for glassmorphism layout ── */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(0, 255, 255, 0.20) !important;
            border-radius: 20px;
            padding: 44px !important;
            backdrop-filter: blur(28px) saturate(200%) brightness(1.12);
            -webkit-backdrop-filter: blur(28px) saturate(200%) brightness(1.12);
            box-shadow:
                0 8px 40px rgba(0, 0, 0, 0.55),
                0 0 0 1px rgba(255, 255, 255, 0.07) inset,
                0 1px 0  rgba(255, 255, 255, 0.10) inset,
                0 0 60px rgba(0, 255, 255, 0.07);
        }

        /* Remove native streamlit border styling around forms inside the card */
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
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
            margin-bottom: 30px;
        }

        /* ── Divider line ── */
        .login-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0,255,255,0.3), transparent);
            margin-bottom: 30px;
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
            margin-top: 18px !important;
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
            margin-top: 14px !important;
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
    """Renders the dark neon login screen and evaluates authentication flow.

    Returns:
        bool: True if authentication configuration passes, False otherwise.
    """
    _inject_login_css()

    st.markdown("<div style='padding-top: 60px;'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        # Utilize a border container to scope the stylized layout correctly
        with st.container(border=True):
            st.markdown(
                """
                <div class="login-icon">🔐</div>
                <div class="login-title">AUDITOR</div>
                <div class="login-subtitle">Secure Access Portal — Enterprise Edition</div>
                <div class="login-divider"></div>
                """,
                unsafe_allow_html=True,
            )

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
                        st.session_state["username"] = username
                        st.session_state["user_name"] = username.upper()
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
