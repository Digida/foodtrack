async def test_list_taxonomies_shape(client, taxonomy):
    resp = await client.get("/api/v1/taxonomy")
    assert resp.status_code == 200
    data = resp.json()
    assert "taxonomies" in data
    names = [t["name"] for t in data["taxonomies"]]
    assert taxonomy.name in names
    item = next(t for t in data["taxonomies"] if t["name"] == taxonomy.name)
    assert item["id"] == taxonomy.id


async def test_list_taxonomies_empty(client):
    resp = await client.get("/api/v1/taxonomy")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"taxonomies": []}
