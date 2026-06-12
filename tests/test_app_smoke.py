"""UI smoke tests via streamlit.testing — script must run without exceptions."""

from streamlit.testing.v1 import AppTest


def test_app_boots_and_shows_disclaimer_and_gate():
    at = AppTest.from_file("app.py").run()
    assert not at.exception
    assert any("Decision-support only" in w.value for w in at.warning)
    # password gate present, no content leaks before auth
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
    assert any("Upload" in h.value for h in at.subheader)
