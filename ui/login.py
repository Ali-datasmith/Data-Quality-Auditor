import streamlit as st
from credentials import validate_credentials


def _inject_login_css() -> None:
    """Inject neon-themed CSS for login page."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace !important;
        }

        .stApp {
            background: linear-gradient(135deg, #0A0E1A 0%, #0D1220 50%, #0A0E1A 100%) !important;
        }

        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .login-card {
            background: rgba(13, 18, 32, 0.95) !important;
            border: 1px solid rgba(0, 255, 255, 0.2) !important;
            border-radius: 12px;
            padding: 48px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 0 40px rgba(0, 255, 255, 0.1) !important;
            backdrop-filter: blur(10px);
        }

        .login-title {
            text-align: center;
            color: #00FFFF !important;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 4px;
            margin-bottom: 12px;
            text-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
        }

        .login-subtitle {
            text-align: center;
            color: rgba(224, 247, 250, 0.5) !important;
            font-size: 12px;
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-bottom: 48px;
        }

        .stTextInput input {
            background-color: rgba(10, 14, 26, 0.8) !important;
            border: 1px solid rgba(0, 255, 255, 0.3) !important;
            color: #E0F7FA !important;
            border-radius: 6px;
            padding: 12px 16px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 14px !important;
        }

        .stTextInput input:focus {
            border-color: #00FFFF !important;
            box-shadow: 0 0 12px rgba(0, 255, 255, 0.3) !important;
        }

        .stTextInput label {
            color: rgba(0, 255, 255, 0.7) !important;
            font-size: 12px !important;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .login-button {
            width: 100% !important;
            margin-top: 24px !important;
        }

        .stButton > button {
            width: 100% !important;
            background: transparent !important;
            border: 1px solid #00FFFF !important;
            color: #00FFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            letter-spacing: 3px;
            text-transform: uppercase;
            padding: 14px 24px !important;
            border-radius: 6px;
            transition: all 0.3s ease !important;
        }

        .stButton > button:hover {
            background: rgba(0, 255, 255, 0.1) !important;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.4) !important;
            transform: translateY(-2px);
        }

        .stAlert {
            background: rgba(231, 76, 60, 0.1) !important;
            border: 1px solid rgba(231, 76, 60, 0.3) !important;
            border-radius: 6px;
            color: #FF6B6B !important;
        }

        .login-footer {
            text-align: center;
            margin-top: 32px;
            font-size: 11px;
            color: rgba(0, 255, 255, 0.3) !important;
            letter-spacing: 1px;
        }

        .demo-creds {
            background: rgba(0, 255, 255, 0.05) !important;
            border: 1px solid rgba(0, 255, 255, 0.15) !important;
            border-radius: 6px;
            padding: 16px;
            margin-top: 32px;
            font-size: 11px;
            color: rgba(0, 255, 255, 0.6) !important;
            letter-spacing: 1px;
            line-height: 1.8;
        }

        .demo-creds strong {
            color: #00FFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login_page() -> bool:
    """
    Render the neon-themed login page.
    Returns True if login was successful.
    """
    _inject_login_css()

    st.markdown(
        """
        <div style="padding-top: 40px;"></div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown(
            """
            <div class="login-card">
                <div class="login-title">🔐 AUDITOR</div>
                <div class="login-subtitle">Secure Access Portal</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_username",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password",
            )

            submit_button = st.form_submit_button(
                "🚀 AUTHENTICATE",
                type="primary",
                )

            if submit_button:
                is_valid, message = validate_credentials(username, password)

                if is_valid:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["user_name"] = username.upper()
                    st.success(message)
                    st.balloons()
                    return True
                else:
                    st.error(message)
                    return False

        st.markdown(
            """
            <div class="demo-creds">
                <strong>📝 DEMO CREDENTIALS</strong><br><br>
                <strong>User 1:</strong> admin / admin<br>
                <strong>User 2:</strong> demo / demo
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="login-footer">
                © 2026 DATA QUALITY AUDITOR | Enterprise Edition
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False
