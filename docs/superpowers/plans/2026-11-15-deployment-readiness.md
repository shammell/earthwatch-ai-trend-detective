# EarthWatch Deployment Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the verified Streamlit application for public hosting and add a Vercel-compatible project entrypoint without falsely claiming that Vercel directly hosts Streamlit.

**Architecture:** Keep Streamlit as the real interactive application because it depends on Streamlit sessions and widgets. Add a static Vercel landing page that links to the hosted Streamlit app and GitHub repository; keep all secrets server-side and optional. Document the two deployment targets and verify the app, static page, tests, and secret handling.

**Tech Stack:** Python 3.11+, Streamlit, NASA POWER API, optional NOAA CDO API, Vercel static deployment, plain HTML/CSS/JavaScript.

---

### Task 1: Add deployment-safe configuration

**Files:**
- Create: `vercel.json`
- Create: `public/index.html`
- Create: `public/earthwatch.css`
- Modify: `README.md`
- Test: `tests/test_deployment_config.py`

- [ ] **Step 1: Write deployment configuration tests**

```python
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_vercel_config_routes_static_landing_page():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config["cleanUrls"] is True
    assert (ROOT / "public" / "index.html").exists()


def test_landing_page_is_honest_about_streamlit_hosting():
    page = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
    assert "Streamlit" in page
    assert "NASA POWER" in page
    assert "GitHub" in page
    assert "not" in page.lower()
```

- [ ] **Step 2: Run the focused test and confirm it fails because deployment files do not exist**

Run: `python -m pytest tests/test_deployment_config.py -q`

Expected: FAIL because `vercel.json` and `public/index.html` are absent.

- [ ] **Step 3: Add the static Vercel landing page and configuration**

`vercel.json` must route `/` to `public/index.html` and enable clean URLs. The landing page must state that the interactive app is Streamlit-hosted, link to the GitHub repository, identify NASA POWER as reanalysis, identify NOAA as optional, and label AppEEARS/GES DISC/Giovanni as planned. Do not include tokens or fabricated live URLs.

- [ ] **Step 4: Document deployment commands and limitations**

Update `README.md` with:

```text
Vercel hosts the project landing page. The interactive Streamlit app must be
deployed to a Streamlit-compatible host because Vercel does not run Streamlit's
persistent widget session server.
```

Document `vercel --prod` for the landing page and Streamlit Community Cloud setup from the GitHub repository. Keep the final public URL as a placeholder until the hosting provider returns it; do not invent one.

- [ ] **Step 5: Run the focused test**

Run: `python -m pytest tests/test_deployment_config.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the deployment surface**

```powershell
git add vercel.json public README.md tests/test_deployment_config.py
git commit -m "feat: add honest deployment landing page"
```

### Task 2: Verify application and deployment artifacts

**Files:**
- Test: `tests/test_deployment_config.py`
- Verify: `app.py`, `requirements.txt`, `.env.example`, `.gitignore`

- [ ] **Step 1: Run the full automated suite**

Run: `python -m pytest -q`

Expected: all tests pass with zero failures.

- [ ] **Step 2: Validate Python syntax and diff formatting**

Run: `python -m py_compile app.py analyzer.py nasa_api.py trend_models.py scene_state.py noaa_api.py source_comparison.py; git diff --check`

Expected: exit code 0.

- [ ] **Step 3: Scan tracked files for secrets**

Run: `git grep -n -i -E 'NOAA_CDO_TOKEN=.{2,}|token.?[:=].{8,}|secret.?[:=].{8,}' -- ':!docs/superpowers/**'`

Expected: only environment-variable lookup code and the empty `.env.example` placeholder are present; no credential value is present.

- [ ] **Step 4: Check the Vercel landing page locally**

Run: `vercel dev --listen 127.0.0.1:3000`

Open `http://127.0.0.1:3000/` and verify the page contains the EarthWatch title, GitHub link, Streamlit hosting explanation, NASA POWER attribution, and honest source-status labels.

### Task 3: Deploy only authenticated, verifiable targets

**Files:**
- Verify: `vercel.json`, `public/index.html`, `README.md`

- [ ] **Step 1: Deploy the static landing page**

Run: `vercel --prod --yes`

Record the exact URL printed by the CLI. Do not report a URL unless the command exits successfully and the URL responds.

- [ ] **Step 2: Verify the deployed URL**

Run: `curl.exe -I <exact-vercel-url>`

Expected: an HTTP success response.

- [ ] **Step 3: Push the final verified commit**

```powershell
git push submission main
git status --short
```

Expected: remote `main` matches local `HEAD`, with a clean worktree.

