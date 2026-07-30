import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute


class TestTaxonomy:
    async def test_create_taxonomy(self, db: AsyncSession):
        t = Taxonomy(name="Fruits", description="Fruit category")
        db.add(t)
        await db.commit()
        assert t.id is not None
        assert t.name == "Fruits"

    async def test_create_node(self, db: AsyncSession, taxonomy: Taxonomy):
        n = TaxonomyNode(taxonomy_id=taxonomy.id, code="FRUITS-01", name="Tropical Fruits")
        db.add(n)
        await db.commit()
        assert n.id is not None
        assert n.taxonomy_id == taxonomy.id

    async def test_create_item(self, db: AsyncSession, taxonomy_node: TaxonomyNode):
        item = TaxonomyItem(
            node_id=taxonomy_node.id,
            code="BANANA-001",
            common_name="Banana",
            scientific_name="Musa acuminata",
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        assert item.id is not None
        assert item.code == "BANANA-001"
        assert item.node_id == taxonomy_node.id

    async def test_item_multilingual_name(self, db: AsyncSession, taxonomy_item: TaxonomyItem):
        name = ItemName(item_id=taxonomy_item.id, language="ar", name="موز")
        db.add(name)
        await db.commit()
        result = await db.execute(
            select(ItemName).where(ItemName.item_id == taxonomy_item.id, ItemName.language == "ar")
        )
        saved = result.scalar_one()
        assert saved.name == "موز"

    async def test_item_attribute(self, db: AsyncSession, taxonomy_item: TaxonomyItem):
        attr = ItemAttribute(
            item_id=taxonomy_item.id, key="calories", value="89", unit="kcal"
        )
        db.add(attr)
        await db.commit()
        assert attr.id is not None
