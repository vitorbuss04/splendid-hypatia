"""
Adversarial Verification Suite for Milestone 1 CSS Design System.
Audits syntax, import resolution, legacy CSS aliases, card-dark clipping, and tabular numeric font inheritance.
"""

import re
from pathlib import Path
import pytest

CSS_DIR = Path("frontend/css")
INDEX_HTML = Path("frontend/index.html")
PREVIEW_HTML = Path("frontend/preview.html")

CSS_MODULES = [
    "tokens.css",
    "base.css",
    "components.css",
    "views.css",
    "animations.css",
    "styles.css",
]

LEGACY_VARIABLES = [
    "--bg-primary",
    "--bg-secondary",
    "--bg-card",
    "--border-color",
    "--text-primary",
    "--text-secondary",
    "--accent",
    "--accent-hover",
    "--success",
    "--warning",
    "--danger",
]


def test_all_css_files_exist():
    """Verify that all 6 required modular CSS files exist in frontend/css/."""
    for filename in CSS_MODULES:
        file_path = CSS_DIR / filename
        assert file_path.exists(), f"Missing CSS file: {file_path}"
        assert file_path.stat().st_size > 0, f"CSS file is empty: {file_path}"


def test_css_balanced_delimiters():
    """
    Adversarial grammar test: Verifies that curly braces, brackets, parentheses,
    and string quotes are strictly balanced across all 6 CSS files.
    """
    for filename in CSS_MODULES:
        path = CSS_DIR / filename
        content = path.read_text(encoding="utf-8")

        stack = []
        in_comment = False
        in_string = None
        escaped = False
        line = 1
        col = 0

        i = 0
        n = len(content)
        while i < n:
            ch = content[i]
            col += 1
            if ch == "\n":
                line += 1
                col = 0

            if in_comment:
                if ch == "*" and i + 1 < n and content[i + 1] == "/":
                    in_comment = False
                    i += 2
                    col += 1
                    continue
                i += 1
                continue

            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == in_string:
                    in_string = None
                i += 1
                continue

            # Check comments
            if ch == "/" and i + 1 < n and content[i + 1] == "*":
                in_comment = True
                i += 2
                col += 1
                continue

            if ch in ('"', "'"):
                in_string = ch
                i += 1
                continue

            if ch in ("{", "(", "["):
                stack.append((ch, line, col))
            elif ch in ("}", ")", "]"):
                matching = {"}": "{", ")": "(", "]": "["}[ch]
                assert stack, f"{filename}:{line}:{col} - Unexpected closing '{ch}'"
                top, l, c = stack.pop()
                assert top == matching, (
                    f"{filename}:{line}:{col} - Mismatched '{ch}', expected match for '{top}' from line {l}:{c}"
                )
            i += 1

        assert not in_comment, f"{filename} - Unterminated comment /*"
        assert not in_string, f"{filename} - Unterminated string {in_string}"
        assert not stack, f"{filename} - Unclosed delimiters: {stack}"


def test_styles_css_imports_resolve():
    """Verify that all @import statements in styles.css point to real files."""
    styles_path = CSS_DIR / "styles.css"
    content = styles_path.read_text(encoding="utf-8")

    # Match @import url('./...') or @import url('...')
    imports = re.findall(r"@import\s+(?:url\(['\"]?([^'\")]+)['\"]?\)|['\"]([^'\"]+)['\"]);", content)
    import_paths = [m[0] or m[1] for m in imports]

    assert len(import_paths) >= 5, f"styles.css should import at least 5 modular stylesheets, found {len(import_paths)}"

    for imp in import_paths:
        if imp.startswith("http://") or imp.startswith("https://"):
            continue  # external CDN URL
        # Relative file import
        clean_rel = imp.replace("./", "")
        resolved = CSS_DIR / clean_rel
        assert resolved.exists(), f"Import '{imp}' in styles.css does not resolve to an existing file: {resolved}"


def test_tokens_legacy_css_variable_aliases():
    """
    Verify that all 11 legacy CSS variables exist as aliases in tokens.css under :root.
    """
    tokens_path = CSS_DIR / "tokens.css"
    content = tokens_path.read_text(encoding="utf-8")

    # Match property declarations inside :root
    root_match = re.search(r":root\s*\{([^}]+)\}", content, re.DOTALL)
    assert root_match, "Could not find :root declaration block in tokens.css"
    root_content = root_match.group(1)

    for var in LEGACY_VARIABLES:
        pattern = rf"{re.escape(var)}\s*:"
        assert re.search(pattern, root_content), f"Legacy variable '{var}' is missing in tokens.css :root block!"


def test_card_dark_overflow_and_border_radius():
    """
    Stress-test .card-dark rules:
    - Check if .card-dark defines border-radius.
    - Check whether .card-dark forces overflow: hidden, and evaluate clipping implications
      on absolute children, tooltips, or top-edge highlight pseudo-elements.
    """
    components_path = CSS_DIR / "components.css"
    content = components_path.read_text(encoding="utf-8")

    # Extract .card-dark base rule
    card_match = re.search(r"\.card-dark\s*\{([^}]+)\}", content)
    assert card_match, "Could not find .card-dark declaration in components.css"
    card_body = card_match.group(1)

    assert "border-radius" in card_body, ".card-dark must specify a border-radius token"
    assert "position: relative" in card_body, ".card-dark must have position: relative for pseudo-element positioning"

    # Check top hairline sheen ::before
    sheen_match = re.search(r"\.card-dark::before\s*\{([^}]+)\}", content)
    assert sheen_match, ".card-dark::before top highlight hairline is required for depth"
    sheen_body = sheen_match.group(1)
    assert "pointer-events: none" in sheen_body, "Hairline must have pointer-events: none to avoid blocking clicks"

    # Clipping evaluation: .card-dark should NOT have overflow: hidden on base rule,
    # because that clips tooltips, modals, and glow drop-shadows.
    assert "overflow: hidden" not in card_body, (
        ".card-dark base rule should NOT force overflow: hidden as it clips tooltips, dropdowns, and ambient glows"
    )


def test_tabular_numbers_inheritance_on_decimal_inputs():
    """
    Adversarial test for numeric inputs:
    Verifies that input[inputmode="decimal"] inherits:
    - font-family: var(--font-mono)
    - font-variant-numeric: tabular-nums
    - font-feature-settings: 'tnum'
    Both in base.css and components.css.
    """
    base_content = (CSS_DIR / "base.css").read_text(encoding="utf-8")
    components_content = (CSS_DIR / "components.css").read_text(encoding="utf-8")

    # In base.css: check input[inputmode="decimal"] selector rule
    assert 'input[inputmode="decimal"]' in base_content, "base.css must style input[inputmode='decimal']"
    assert "tabular-nums" in base_content, "base.css must enforce tabular-nums on numeric inputs"

    # In components.css: check input[inputmode="decimal"]
    assert 'input[inputmode="decimal"]' in components_content, (
        "components.css must reinforce tabular-nums on input[inputmode='decimal']"
    )
    assert "tabular-nums" in components_content, "components.css must enforce tabular-nums"


def test_html_includes_required_font_and_css_links():
    """Verify that both index.html and preview.html link to fonts and styles.css."""
    for html_path in [INDEX_HTML, PREVIEW_HTML]:
        content = html_path.read_text(encoding="utf-8")
        assert "Inter" in content, f"{html_path} missing Inter font link"
        assert "JetBrains+Mono" in content, f"{html_path} missing JetBrains Mono font link"
        assert "styles.css" in content, f"{html_path} missing styles.css link"


def test_resina_material_badge_exists():
    """Verify that .badge-mat-resina is present in components.css."""
    content = (CSS_DIR / "components.css").read_text(encoding="utf-8")
    assert ".badge-mat-resina" in content, "Missing .badge-mat-resina in components.css"
