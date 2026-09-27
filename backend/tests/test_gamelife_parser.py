from scrapers.gamelife import _parse_grid


def test_gamelife_grid_exposes_platform_before_product_fetch():
    html = """
    <div class="oe_product">
      <a href="/swp30080-tekken-6"><h2>Tekken 6 - PlayStation 5</h2></a>
      <img class="oe_product_image_img" src="/web/image/product/1/image_512" />
    </div>
    <div class="oe_product">
      <a href="/cop-controller-tekken-8"><h2>Controller Tekken 8</h2></a>
    </div>
    """

    results = _parse_grid(html)

    assert results[0]["platform"] == "PS5"
    assert results[0]["is_game"] is True
    assert results[1]["is_game"] is False