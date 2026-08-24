"""Download the Google Fonts used by the UI into static/vendor/fonts/.

Keeps the project self-contained so the interface renders identically without
an internet connection (e.g. during the diploma defence).

Usage: python scripts/vendor_fonts.py
"""
import re
import subprocess
from pathlib import Path

FONT_CSS_URL = (
    'https://fonts.googleapis.com/css2'
    '?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700'
    '&family=Inter:wght@300;400;500;600;700'
    '&display=swap'
)

# Google serves woff2 only to browsers that advertise support.
UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
)

WANTED_SUBSETS = {'latin', 'latin-ext'}

OUT_DIR = Path(__file__).resolve().parent.parent / 'static' / 'vendor' / 'fonts'


def fetch(url: str) -> bytes:
    """Fetch over curl, which already trusts the system certificate store."""
    result = subprocess.run(
        ['curl', '-sSL', '--fail', '-A', UA, url],
        capture_output=True, check=True,
    )
    return result.stdout


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    css = fetch(FONT_CSS_URL).decode('utf-8')

    # The stylesheet is a sequence of "/* subset */ @font-face { ... }" blocks.
    blocks = re.findall(r'/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{[^}]*\})', css)
    kept = []

    for subset, block in blocks:
        if subset not in WANTED_SUBSETS:
            continue

        url_match = re.search(r"url\((https://[^)]+\.woff2)\)", block)
        family_match = re.search(r"font-family:\s*'([^']+)'", block)
        weight_match = re.search(r'font-weight:\s*([\d\s]+)', block)
        if not (url_match and family_match):
            continue

        family = family_match.group(1).replace(' ', '')
        weight = (weight_match.group(1).strip().replace(' ', '-') if weight_match else 'regular')
        filename = f'{family}-{weight}-{subset}.woff2'

        (OUT_DIR / filename).write_bytes(fetch(url_match.group(1)))
        kept.append(block.replace(url_match.group(1), filename))
        print(f'{filename}')

    header = (
        '/* Self-hosted Google Fonts (DM Sans, Inter).\n'
        '   Regenerate with: python scripts/vendor_fonts.py */\n\n'
    )
    (OUT_DIR / 'fonts.css').write_text(header + '\n\n'.join(kept) + '\n', encoding='utf-8')
    print(f'\n{len(kept)} @font-face rules -> {OUT_DIR / "fonts.css"}')


if __name__ == '__main__':
    main()
