from fastapi.testclient import TestClient

from blackbox.app import create_app


def test_dashboard_serves_the_local_ui(tmp_path):
    client = TestClient(create_app(str(tmp_path / 'events.db'), str(tmp_path)))

    page = client.get('/')
    assert page.status_code == 200
    assert page.headers['content-type'].startswith('text/html')
    assert 'BLACKBOX' in page.text
    assert '/ui/app.js' in page.text

    script = client.get('/ui/app.js')
    assert script.status_code == 200
    assert 'loadIncidents' in script.text

    styles = client.get('/ui/styles.css')
    assert styles.status_code == 200
    assert '--accent' in styles.text


def test_dashboard_does_not_replace_the_json_api(tmp_path):
    client = TestClient(create_app(str(tmp_path / 'events.db'), str(tmp_path)))

    incidents = client.get('/incidents')
    assert incidents.status_code == 200
    assert incidents.json() == []
