from app.pipeline.snapshot import build_snapshot


def test_build_snapshot_extracts_metadata_and_stable_hash():
    html = """
    <html>
      <head>
        <title>Example Product</title>
        <meta name="description" content="A useful product.">
      </head>
      <body>
        <nav>Ignore navigation</nav>
        <main><h1>Build faster</h1><p>Ship reliable software.</p></main>
      </body>
    </html>
    """

    first = build_snapshot(
        website_url="https://example.com",
        final_url="https://www.example.com/",
        html=html,
        status_code=200,
    )
    second = build_snapshot(
        website_url="https://example.com",
        final_url="https://www.example.com/",
        html=html,
        status_code=200,
    )

    assert first.page_title == "Example Product"
    assert first.page_description == "A useful product."
    assert first.content_text == "Build faster Ship reliable software."
    assert first.content_hash == second.content_hash
    assert first.metadata == {"status_code": 200, "character_count": 36}


def test_build_snapshot_hash_changes_with_visible_content():
    first = build_snapshot(
        website_url="https://example.com",
        final_url="https://example.com",
        html="<main><p>Old positioning</p></main>",
        status_code=200,
    )
    second = build_snapshot(
        website_url="https://example.com",
        final_url="https://example.com",
        html="<main><p>New positioning</p></main>",
        status_code=200,
    )

    assert first.content_hash != second.content_hash
