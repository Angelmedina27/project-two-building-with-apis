import pytest

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


def test_htmx_requests_get_only_the_list_region(client, user, make_item):
    make_item(title="Severance", media_type="tv")
    client.force_login(user)

    response = client.get("/watchlist/?media_type=tv", **HTMX)
    html = response.content.decode()

    assert response.status_code == 200
    assert "Severance" in html
    assert "<html" not in html
    assert 'id="watchlist-results"' not in html
    assert "HX-Request" in response["Vary"]


def test_normal_requests_get_the_full_page_with_controls(client, user, make_item):
    make_item(title="Severance", media_type="tv")
    client.force_login(user)

    response = client.get("/watchlist/?media_type=tv")
    html = response.content.decode()

    assert "<html" in html
    assert 'id="watchlist-results"' in html
    assert 'hx-get="/watchlist/"' in html and 'hx-push-url="true"' in html
    assert "HX-Request" in response["Vary"]


def test_history_restore_requests_get_the_full_page(client, user):
    client.force_login(user)
    html = client.get(
        "/watchlist/", HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"
    ).content.decode()
    assert "<html" in html


def test_controls_show_the_current_selection(client, user, make_item):
    make_item()
    client.force_login(user)
    html = client.get(
        "/watchlist/?q=dune&status=watched&media_type=movie&sort=rating"
    ).content.decode()

    assert 'name="q" value="dune"' in html
    assert '<option value="watched" selected>Watched</option>' in html
    assert '<option value="movie" selected>Movies</option>' in html
    assert '<option value="rating" selected>My rating</option>' in html


def test_unknown_values_fall_back_to_the_defaults_in_the_controls(client, user, make_item):
    make_item(title="Severance")
    client.force_login(user)
    response = client.get("/watchlist/?status=binged&media_type=game&sort=chaos&page=-4")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Severance" in html
    assert '<option value="recent" selected>Recently added</option>' in html
    assert " selected>" not in html.replace(
        '<option value="recent" selected>Recently added</option>', ""
    )


def test_filtered_view_with_no_matches_shows_the_filtered_empty_state(client, user, make_item):
    make_item(status="plan")
    client.force_login(user)
    html = client.get("/watchlist/?status=dropped", **HTMX).content.decode()

    assert "No titles on your watchlist match these filters." in html
    assert "Your watchlist is empty." not in html
    assert '<a href="/watchlist/" class="btn btn-sm">Clear filters</a>' in html
    assert '<a href="/search/" class="btn btn-primary btn-sm">Search TMDB</a>' in html
    assert "<table" not in html


def test_anonymous_htmx_list_update_gets_an_hx_redirect(client):
    response = client.get("/watchlist/?status=watching&page=2", **HTMX)

    assert response.status_code == 200
    assert (
        response["HX-Redirect"]
        == "/accounts/login/?next=/watchlist/%3Fstatus%3Dwatching%26page%3D2"
    )


def test_anonymous_normal_request_gets_a_standard_redirect(client):
    response = client.get("/watchlist/?sort=title")

    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/?next=/watchlist/%3Fsort%3Dtitle"
