"""Script to convert BAO_CAO_CHALLENGE_A_HOAN_CHINH.md to a beautifully styled PDF."""
import os
import subprocess
import sys
import markdown
from pygments.formatters import HtmlFormatter

def build_pdf():
    md_file = "BAO_CAO_CHALLENGE_A_HOAN_CHINH.md"
    html_file = "tmp_report.html"
    pdf_file = "BAO_CAO_CHALLENGE_A_HOAN_CHINH.pdf"

    if not os.path.exists(md_file):
        print(f"Error: {md_file} not found.")
        return 1

    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Pygments syntax highlighting CSS
    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".codehilite")

    # Convert Markdown to HTML
    html_content = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "nl2br", "sane_lists"],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "codehilite",
                "linenums": False,
            }
        }
    )

    # CSS for high-quality printing / PDF generation
    css_style = f"""
    @page {{
        size: A4 portrait;
        margin: 18mm 16mm 20mm 16mm;
        @bottom-right {{
            content: "Trang " counter(page) " / " counter(pages);
            font-size: 8.5pt;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #64748b;
        }}
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.58;
        color: #1e293b;
        background: #ffffff;
        margin: 0;
        padding: 0;
    }}

    /* Header styling */
    h1:first-of-type {{
        font-size: 18pt;
        font-weight: 800;
        color: #0f172a;
        text-align: center;
        letter-spacing: -0.02em;
        margin-top: 0;
        margin-bottom: 4px;
        text-transform: uppercase;
    }}

    h1:nth-of-type(2) {{
        font-size: 13pt;
        font-weight: 700;
        color: #1d4ed8;
        text-align: center;
        letter-spacing: -0.01em;
        margin-top: 0;
        margin-bottom: 18px;
        padding-bottom: 12px;
        border-bottom: 2px solid #e2e8f0;
    }}

    h2 {{
        font-size: 12pt;
        font-weight: 700;
        color: #0f172a;
        margin-top: 24px;
        margin-bottom: 10px;
        padding-left: 10px;
        border-left: 4px solid #2563eb;
        page-break-after: avoid;
        break-after: avoid;
    }}

    h3 {{
        font-size: 10.5pt;
        font-weight: 700;
        color: #1e293b;
        margin-top: 16px;
        margin-bottom: 6px;
        page-break-after: avoid;
        break-after: avoid;
    }}

    h4 {{
        font-size: 10pt;
        font-weight: 600;
        color: #334155;
        margin-top: 12px;
        margin-bottom: 4px;
        page-break-after: avoid;
        break-after: avoid;
    }}

    p {{
        margin-top: 0;
        margin-bottom: 10px;
        text-align: justify;
    }}

    hr {{
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 18px 0;
    }}

    /* Info Box / Metadata block */
    h2:first-of-type + ul,
    h2:first-of-type + p + ul {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 18px 12px 34px;
        margin-bottom: 20px;
        font-size: 9.5pt;
    }}

    ul, ol {{
        margin-top: 0;
        margin-bottom: 10px;
        padding-left: 22px;
    }}

    li {{
        margin-bottom: 4px;
    }}

    strong {{
        color: #0f172a;
        font-weight: 600;
    }}

    /* Tables */
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 14px 0 16px 0;
        font-size: 8.8pt;
        page-break-inside: avoid;
        break-inside: avoid;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        overflow: hidden;
    }}

    th, td {{
        padding: 6px 9px;
        text-align: left;
        vertical-align: top;
        border: 1px solid #cbd5e1;
        line-height: 1.45;
    }}

    th {{
        background: #f1f5f9;
        color: #0f172a;
        font-weight: 700;
        border-bottom: 2px solid #94a3b8;
    }}

    tr:nth-child(even) td {{
        background: #f8fafc;
    }}

    tr:hover td {{
        background: #f1f5f9;
    }}

    /* Code & Pre */
    code {{
        font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
        font-size: 8.8pt;
        background: #f1f5f9;
        color: #0f172a;
        padding: 2px 5px;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
    }}

    pre, .codehilite {{
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 10px 12px;
        margin: 10px 0 14px 0;
        overflow-x: auto;
        font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
        font-size: 8.2pt;
        line-height: 1.45;
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    pre code {{
        background: transparent;
        padding: 0;
        border: none;
        color: inherit;
        font-size: inherit;
    }}

    /* Links */
    a {{
        color: #2563eb;
        text-decoration: none;
    }}

    a:hover {{
        text-decoration: underline;
    }}

    /* Quotes / Callouts */
    blockquote {{
        margin: 12px 0;
        padding: 8px 14px;
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        color: #1e40af;
        border-radius: 0 6px 6px 0;
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    /* Badges & highlights */
    .badge {{
        display: inline-block;
        padding: 2px 7px;
        font-size: 8pt;
        font-weight: 600;
        border-radius: 9999px;
        background: #dbeafe;
        color: #1e40af;
    }}

    /* Printing optimizations */
    @media print {{
        body {{
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        .no-print {{
            display: none !important;
        }}
        h2, h3, h4 {{
            page-break-after: avoid;
            break-after: avoid;
        }}
        table, pre, blockquote {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}
    }}

    {pygments_css}
    """

    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <title>Báo cáo Challenge A - Persistent Memory</title>
    <style>
        {css_style}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    # Convert HTML to PDF using Microsoft Edge headless
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    abs_html = os.path.abspath(html_file)
    abs_pdf = os.path.abspath(pdf_file)

    cmd = [
        edge_path,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={abs_pdf}",
        abs_html
    ]

    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("Return code:", res.returncode)
    if res.stdout:
        print("Stdout:", res.stdout)
    if res.stderr:
        print("Stderr:", res.stderr)

    if os.path.exists(abs_pdf):
        size_kb = os.path.getsize(abs_pdf) / 1024
        print(f"SUCCESS: Generated {pdf_file} ({size_kb:.1f} KB)")
        # Clean up temporary HTML file
        if os.path.exists(html_file):
            os.remove(html_file)
        return 0
    else:
        print("ERROR: PDF was not generated.")
        return 1

if __name__ == "__main__":
    sys.exit(build_pdf())
