from sqlalchemy import select

from app.models.taxonomy import TaxonomyItem
from app.models.tracking import Collection, CollectionItem
from app.services.collection_service import seed_collections_from_taxonomy


async def test_seed_collections_from_taxonomy(db, taxonomy, taxonomy_node, taxonomy_item):
    result = await seed_collections_from_taxonomy(db, taxonomy.id)
    assert result == {"nodes": 1, "collections": 1, "items": 1}

    collections = (await db.execute(select(Collection))).scalars().all()
    assert len(collections) == 1
    assert collections[0].name == taxonomy_node.name
    assert collections[0].slug == "test-node"

    items = (await db.execute(select(CollectionItem))).scalars().all()
    assert [i.item_id for i in items] == [taxonomy_item.id]
    assert items[0].collection_id == collections[0].id


async def test_seed_collections_is_idempotent(db, taxonomy, taxonomy_node, taxonomy_item):
    first = await seed_collections_from_taxonomy(db, taxonomy.id)
    second = await seed_collections_from_taxonomy(db, taxonomy.id)
    assert first["collections"] == 1
    assert first["items"] == 1
    assert second == {"nodes": 1, "collections": 0, "items": 0}

    collections = (await db.execute(select(Collection))).scalars().all()
    assert len(collections) == 1
    items = (await db.execute(select(CollectionItem))).scalars().all()
    assert len(items) == 1


async def test_seed_collections_links_new_items_on_rerun(db, taxonomy, taxonomy_node, taxonomy_item):
    await seed_collections_from_taxonomy(db, taxonomy.id)

    extra = TaxonomyItem(
        node_id=taxonomy_node.id,
        code="TEST-ITEM-002",
        common_name="Extra Item",
    )
    db.add(extra)
    await db.commit()

    # The category now has 2 items (not exhausted): target = 2 collections.
    # The existing base collection picks up the new item and one new
    # "selection" collection is created.
    result = await seed_collections_from_taxonomy(db, taxonomy.id)
    assert result["collections"] == 1
    assert result["items"] == 3

    items = (await db.execute(select(CollectionItem))).scalars().all()
    assert len(items) == 4


async def test_seed_collections_no_taxonomy(db):
    result = await seed_collections_from_taxonomy(db)
    assert result == {"nodes": 0, "collections": 0, "items": 0}


async def test_seed_collections_reaches_target_for_rich_category(db, taxonomy, taxonomy_node):
    for i in range(12):
        db.add(TaxonomyItem(node_id=taxonomy_node.id, code=f"T{i:03d}", common_name=f"Item {i}"))
    await db.commit()

    result = await seed_collections_from_taxonomy(db, taxonomy.id)
    assert result["nodes"] == 1
    assert result["collections"] == 10

    collections = (await db.execute(select(Collection))).scalars().all()
    assert len(collections) == 10
    slugs = [c.slug for c in collections]
    assert len(set(slugs)) == 10


async def test_seed_collections_exhausted_small_category(db, taxonomy, taxonomy_node):
    for i in range(2):
        db.add(TaxonomyItem(node_id=taxonomy_node.id, code=f"X{i:03d}", common_name=f"X {i}"))
    await db.commit()

    result = await seed_collections_from_taxonomy(db, taxonomy.id)
    assert result["collections"] == 2

    collections = (await db.execute(select(Collection))).scalars().all()
    assert len(collections) == 2


async def test_seed_collections_facet_themes(db, taxonomy, taxonomy_node):
    rows = [
        ("ANIMAL-A", "A", "Chordata", ""),
        ("ANIMAL-B", "B", "Chordata", ""),
        ("ANIMAL-C", "C", "Chordata", ""),
        ("BAKERY-A", "Bread A", "Magnoliophyta", "Bread flour; baking staple"),
        ("BAKERY-B", "Bread B", "Magnoliophyta", "Baking and bread"),
        ("BAKERY-C", "Bread C", "Magnoliophyta", "Sourdough bread"),
    ]
    for code, name, phylum, uses in rows:
        db.add(TaxonomyItem(
            node_id=taxonomy_node.id, code=code, common_name=name,
            phylum=phylum, local_uses=uses,
        ))
    await db.commit()

    result = await seed_collections_from_taxonomy(db, taxonomy.id)
    collections = (await db.execute(select(Collection))).scalars().all()
    names = {c.name for c in collections}

    assert "Test Node — Animal-Derived" in names
    assert "Test Node — Baking & Bakery" in names
    assert result["collections"] == 6
