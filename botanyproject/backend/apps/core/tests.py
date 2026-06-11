from django.urls import reverse


def test_health_endpoint_returns_checks(client):
    """Health endpoint responds and reports each dependency (ТЗ Этап 5.19)."""
    response = client.get(reverse("v1:core:health"))
    assert response.status_code in (200, 503)
    body = response.json()
    assert "checks" in body
    assert set(body["checks"]) == {"database", "redis", "elasticsearch", "s3"}
