import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_vercel_config_and_landing_page_exist():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config["cleanUrls"] is True
    assert (ROOT / "public" / "index.html").exists()
    assert (ROOT / "public" / "earthwatch.css").exists()


def test_landing_page_is_honest_about_streamlit_hosting():
    page = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
    assert "Streamlit" in page
    assert "NASA POWER" in page
    assert "GitHub" in page
    assert "not" in page.lower()
