def test_openapi_has_custom_fields_and_filter_routes(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200, r.text
    paths = set(r.json()["paths"].keys())

    # Custom fields router paths:contentReference[oaicite:11]{index=11}:contentReference[oaicite:12]{index=12}:contentReference[oaicite:13]{index=13}
    assert "/workspaces/{workspace_id}/custom-fields" in paths  # POST, GET
    assert "/lists/{list_id}/custom-fields/{field_id}/enable" in paths
    assert "/tasks/{task_id}/custom-fields/{field_id}" in paths

    # Tasks filter router prefix "/workspaces":contentReference[oaicite:14]{index=14} -> POST /workspaces/{wid}/tasks/filter:contentReference[oaicite:15]{index=15}
    assert "/workspaces/{workspace_id}/tasks/filter" in paths
