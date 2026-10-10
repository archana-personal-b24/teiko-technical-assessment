from teiko.config import Settings
from teiko.dashboard import DashboardFactory


def test_dashboard_and_health_endpoint(pipeline_db, tmp_path):
    settings = Settings(tmp_path, tmp_path / "unused.csv", pipeline_db)
    application = DashboardFactory(settings).create()
    client = application.server.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"dash-renderer" in response.data
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json == {"status": "ok"}
