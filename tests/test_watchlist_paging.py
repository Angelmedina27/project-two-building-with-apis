import re
from html import unescape
from urllib.parse import parse_qs, urlsplit

import pytest

pytestmark = pytest.mark.django_db


def link_params(html, label):
    """The query parameters of the pagination link with this label (e.g. "Next")."""
    match = re.search(rf'<a href="([^"]+)"[^>]*>[^<]*{label}', html)
    assert match, f"no {label} link"
    return parse_qs(urlsplit(unescape(match.group(1))).query)


def test_bad_pages_fall_back_to_the_nearest_page_and_links_keep_parameters(client, user, make_item):
    for n in range(1, 13):
        make_item(tmdb_id=n, title=f"Title {n:02}", status="watching")
    make_item(tmdb_id=99, title="Title 00 Planned", status="plan")  # Filtered out.
    client.force_login(user)

    # Past the end: the last page (12 matches at 10 per page -> page 2 of 2).
    html = client.get("/watchlist/?status=watching&sort=title&page=99").content.decode()
    assert "Page 2 of 2" in html
    assert "Title 11" in html and "Title 12" in html
    assert "Title 10" not in html
    assert link_params(html, "Previous") == {
        "status": ["watching"],
        "sort": ["title"],
        "page": ["1"],
    }

    # Not a number: the first page, with Next keeping the same parameters.
    html = client.get("/watchlist/?status=watching&sort=title&page=abc").content.decode()
    assert "Page 1 of 2" in html
    assert "Title 01" in html and "Title 10" in html
    assert "Title 11" not in html and "Planned" not in html
    assert link_params(html, "Next") == {
        "status": ["watching"],
        "sort": ["title"],
        "page": ["2"],
    }


def test_ten_items_per_page_and_links_keep_q_and_media_type(client, user, make_item):
    for n in range(1, 24):
        make_item(tmdb_id=n, title=f"Dune {n:02}", media_type="tv")
    make_item(tmdb_id=99, title="Dune Movie", media_type="movie")
    client.force_login(user)

    html = client.get("/watchlist/?q=dune&media_type=tv&page=2").content.decode()

    assert "Page 2 of 3" in html
    assert "23 titles" in html
    assert html.count('<tr id="item-') == 10
    assert link_params(html, "Next") == {"q": ["dune"], "media_type": ["tv"], "page": ["3"]}
    assert link_params(html, "Previous") == {"q": ["dune"], "media_type": ["tv"], "page": ["1"]}


def test_a_single_page_shows_no_pagination(client, user, make_item):
    make_item()
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    assert "Page 1 of 1" not in html
    assert "Previous" not in html and "Next" not in html
