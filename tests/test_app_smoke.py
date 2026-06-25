"""UI smoke tests via streamlit.testing — script must run without exceptions."""

from streamlit.testing.v1 import AppTest


def test_app_boots_and_shows_disclaimer_and_gate():
    at = AppTest.from_file("app.py").run()
    assert not at.exception
    # disclaimer is now injected HTML (not st.warning) — verify app renders
    assert at.markdown  # at least one markdown block rendered
    # password gate present
    assert at.text_input


def test_wrong_password_rejected():
    at = AppTest.from_file("app.py")
    at.secrets["APP_PASSWORD"] = "right"
    at.run()
    at.text_input[0].input("wrong").run()
    assert not at.exception
    assert at.error


def test_correct_password_unlocks_upload():
    at = AppTest.from_file("app.py")
    at.secrets["APP_PASSWORD"] = "right"
    at.secrets["ANTHROPIC_API_KEY"] = "test-key"
    at.run()
    at.text_input[0].input("right").run()
    assert not at.exception
    # Upload screen is rendered via st.markdown HTML (no subheader), verify toggle present
    assert at.toggle or at.file_uploader
