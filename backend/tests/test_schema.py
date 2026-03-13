def test_get_schema(client):
    response = client.get("/api/schema")
    assert response.status_code == 200

    data = response.json()
    assert "tables" in data

    table_names = [t["name"] for t in data["tables"]]
    assert "projects" in table_names
    assert "benchmark_runs" in table_names
    assert "run_metrics" in table_names

    # Check projects table structure
    projects = next(t for t in data["tables"] if t["name"] == "projects")
    col_names = [c["name"] for c in projects["columns"]]
    assert "id" in col_names
    assert "name" in col_names

    # Check id column has correct constraints
    id_col = next(c for c in projects["columns"] if c["name"] == "id")
    assert id_col["primary_key"] is True
    assert id_col["nullable"] is False
    assert id_col["type"] == "INTEGER"

    # Check name column is unique
    name_col = next(c for c in projects["columns"] if c["name"] == "name")
    assert name_col["unique"] is True


def test_schema_foreign_keys(client):
    response = client.get("/api/schema")
    data = response.json()

    runs = next(t for t in data["tables"] if t["name"] == "benchmark_runs")
    fk_cols = [fk["column"] for fk in runs["foreign_keys"]]
    assert "project_id" in fk_cols
    assert "model_version_id" in fk_cols
    assert "dataset_version_id" in fk_cols

    # Check FK references
    project_fk = next(fk for fk in runs["foreign_keys"] if fk["column"] == "project_id")
    assert project_fk["references_table"] == "projects"
    assert project_fk["references_column"] == "id"


def test_schema_unique_constraints(client):
    response = client.get("/api/schema")
    data = response.json()

    run_metrics = next(t for t in data["tables"] if t["name"] == "run_metrics")
    uq_names = [uq["name"] for uq in run_metrics["unique_constraints"]]
    assert "uq_run_metric" in uq_names

    uq = next(u for u in run_metrics["unique_constraints"] if u["name"] == "uq_run_metric")
    assert sorted(uq["columns"]) == ["metric_id", "run_id"]


def test_schema_sync_in_sync(client):
    """When DB was created from models (as in tests), sync should report in_sync."""
    response = client.get("/api/schema/sync")
    assert response.status_code == 200

    data = response.json()
    assert "in_sync" in data
    assert "differences" in data
    assert data["in_sync"] is True
    assert data["differences"] == []
