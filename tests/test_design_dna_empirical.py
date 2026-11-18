"""
Automated empirical test suite validating DESIGN_DNA.md against the actual frontend codebase.
Verifies token declarations, component selectors, resets, and contract invariants.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_DNA_PATH = REPO_ROOT / "DESIGN_DNA.md"
FRONTEND_DIR = REPO_ROOT / "frontend"
CSS_DIR = FRONTEND_DIR / "css"


@pytest.fixture(scope="module")
def design_dna_content():
    assert DESIGN_DNA_PATH.exists(), "DESIGN_DNA.md must exist at repository root"
    return DESIGN_DNA_PATH.read_text(encoding="utf-8")


def test_design_dna_exists_and_covers_required_chapters(design_dna_content):
    """Verifies that DESIGN_DNA.md exists, has substantial content, and contains all required chapters/sections."""
    assert len(design_dna_content) > 25000, "DESIGN_DNA.md must be a comprehensive document (>25KB)"
    
    # Check all major chapters
    for i in range(1, 8):
        assert f"## {i}." in design_dna_content, f"Chapter {i} must be present in DESIGN_DNA.md"
        
    # Check critical sections added/refined in Milestone 2
    assert "### 1.4 Global Resets" in design_dna_content
    assert "### 2.14 Timing, Easings & Interactive Transitions Tokens" in design_dna_content
    assert "### 3.3 Complete Typographic Scale Hierarchy" in design_dna_content
    assert "### 5.9 Motion Physics, Easings & Interactive Transition Curves" in design_dna_content
    assert "### 6.10 Catalog Cards, Cost Distribution & Production Failure Tracking" in design_dna_content
    assert "### 7.8 Critical Contract Invariants & Protected Identifiers" in design_dna_content
    assert "### 7.9 Architectural Precedence: Dual-Layer Specificity & Tailwind Utility Overrides" in design_dna_content


def test_design_dna_motion_tokens_match_tokens_css(design_dna_content):
    """Verifies that motion/transition tokens documented in DESIGN_DNA.md exist verbatim in tokens.css."""
    tokens_css = (CSS_DIR / "tokens.css").read_text(encoding="utf-8")
    
    expected_tokens = [
        "--ease-out",
        "--ease-in-out",
        "--ease-spring",
        "--transition-fast",
        "--transition-normal",
        "--transition-slow",
    ]
    
    for token in expected_tokens:
        assert token in tokens_css, f"Token {token} must exist in tokens.css"
        assert token in design_dna_content, f"Token {token} must be documented in DESIGN_DNA.md"

    # Verify spring cubic-bezier value
    assert "cubic-bezier(0.16, 1, 0.3, 1)" in tokens_css
    assert "cubic-bezier(0.16, 1, 0.3, 1)" in design_dna_content


def test_design_dna_resets_match_base_css(design_dna_content):
    """Verifies that global reset rules documented in Section 1.4 match base.css."""
    base_css = (CSS_DIR / "base.css").read_text(encoding="utf-8")
    
    # 1. Smooth scroll across containers
    assert "scroll-behavior: smooth;" in base_css
    assert "scroll-behavior: smooth;" in design_dna_content
    
    # 2. Color scheme dark and font smoothing on html
    assert "color-scheme: dark;" in base_css
    assert "color-scheme: dark;" in design_dna_content
    
    # 3. Body canvas min-height: 100vh
    assert "min-height: 100vh;" in base_css
    assert "min-height: 100vh;" in design_dna_content
    
    # 4. Selection background color rgba(37, 99, 235, 0.40)
    assert "rgba(37, 99, 235, 0.40)" in base_css
    assert "rgba(37, 99, 235, 0.40)" in design_dna_content
    
    # 5. Scrollbar semantic tokens
    assert "var(--border-default)" in base_css
    assert "var(--border-hover)" in base_css
    assert "var(--radius-full)" in base_css


def test_design_dna_omitted_components_cataloged(design_dna_content):
    """Verifies that all previously omitted components are properly documented and exist in code."""
    components_css = (CSS_DIR / "components.css").read_text(encoding="utf-8")
    views_css = (CSS_DIR / "views.css").read_text(encoding="utf-8")
    index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    
    # 1. card-dark-featured
    assert ".card-dark-featured" in components_css
    assert ".card-dark-featured" in design_dna_content
    
    # 2. form-input-dark
    assert ".form-input-dark" in components_css
    assert ".form-input-dark" in design_dna_content
    
    # 3. printer-card and printer-rate-box
    assert ".printer-card" in views_css
    assert ".printer-rate-box" in views_css
    assert ".printer-card" in design_dna_content
    assert ".printer-rate-box" in design_dna_content
    
    # 4. filament catalog items
    assert ".filament-card" in views_css
    assert ".filament-cost-box" in views_css
    assert ".filament-swatch" in views_css
    assert ".filament-swatch-dot" in views_css
    assert "#filament-name-preview-box" in views_css
    assert ".filament-card" in design_dna_content
    assert ".filament-cost-box" in design_dna_content
    assert ".filament-swatch" in design_dna_content
    assert ".filament-swatch-dot" in design_dna_content
    assert "#filament-name-preview-box" in design_dna_content
    
    # 5. cost-distribution-bar
    assert ".cost-distribution-bar" in views_css
    assert "cost-distribution-bar" in index_html
    assert ".cost-distribution-bar" in design_dna_content
    
    # 6. chart-card
    assert ".chart-card" in views_css
    assert ".chart-card" in design_dna_content
    
    # 7. dashboard-empty-banner
    assert 'id="dashboard-empty-banner"' in index_html
    assert "#dashboard-empty-banner" in design_dna_content
    
    # 8. project-filter-chip
    assert "project-filter-chip" in index_html
    assert ".project-filter-chip" in design_dna_content
    
    # 9. modal-failure
    assert 'id="modal-failure"' in index_html
    assert "#modal-failure" in design_dna_content


def test_design_dna_versioned_stylesheet_links(design_dna_content):
    """Verifies that versioned stylesheet links in index.html are cited correctly in DESIGN_DNA.md."""
    index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    
    for link in ["styles.css?v=1.4.3", "components.css?v=1.4.3", "views.css?v=1.4.3"]:
        assert link in index_html, f"Link {link} must exist in frontend/index.html"
        assert link in design_dna_content, f"Link {link} must be cited in DESIGN_DNA.md"


def test_design_dna_typographic_citations(design_dna_content):
    """Verifies typographic scale citations in Table 3.3."""
    app_js = (FRONTEND_DIR / "js" / "app.js").read_text(encoding="utf-8")
    components_css = (CSS_DIR / "components.css").read_text(encoding="utf-8")
    
    # Line 153 in components.css
    lines = components_css.splitlines()
    assert "font-size: 0.8125rem;" in lines[152], "Line 153 of components.css must declare font-size: 0.8125rem;"
    assert "components.css:153" in design_dna_content
    
    # app.js empty state / card title lines
    assert "app.js:2636, 2674, 2928" in design_dna_content


def test_design_dna_dual_layer_specificity_architecture(design_dna_content):
    """Verifies that Section 7.9 documents the specificity cascade and prescribed modification workflows."""
    assert "5-Level Specificity Cascade" in design_dna_content or "5-level" in design_dna_content.lower()
    assert "LEVEL 4: Modular Component Rules with !important" in design_dna_content
    assert "!bg-purple-600" in design_dna_content
    assert ".btn-primary" in design_dna_content
