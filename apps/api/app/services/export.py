from __future__ import annotations

import asyncio
import markdown


async def generate_pdf(content_md: str) -> bytes:
    """Convert Markdown memo to PDF via WeasyPrint."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _render_pdf, content_md)


def _render_pdf(content_md: str) -> bytes:
    from weasyprint import HTML

    html_body = markdown.markdown(content_md, extensions=["tables", "fenced_code"])
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; color: #1a1a1a; line-height: 1.6; }}
  h1 {{ font-size: 2em; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; }}
  h2 {{ font-size: 1.4em; margin-top: 2em; color: #2c2c2c; }}
  h3 {{ font-size: 1.1em; color: #3c3c3c; }}
  p {{ margin: 0.8em 0; }}
  ul {{ padding-left: 1.5em; }}
  li {{ margin: 0.3em 0; }}
  em {{ color: #555; }}
  strong {{ color: #111; }}
</style>
</head>
<body>{html_body}</body>
</html>"""
    return HTML(string=html).write_pdf()
