"""Share & Social service: link generation, peer comparison, multi-platform sharing."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product import Product


async def generate_share_links(product_sku: str, product_name: str) -> dict:
    base_url = "https://foodtrack.ag"
    share_data = f"{base_url}/verify/{product_sku}"
    return {
        "product_sku": product_sku,
        "product_name": product_name,
        "share_url": share_data,
        "social_links": {
            "whatsapp": f"https://wa.me/?text={share_data}",
            "twitter": f"https://twitter.com/intent/tweet?text=Verify+food+provenance+at+{share_data}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={share_data}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={share_data}",
            "telegram": f"https://t.me/share/url?url={share_data}",
            "email": f"mailto:?subject=Food+Provenance+Verification&body={share_data}",
        },
    }


async def get_peer_comparison(db: AsyncSession, product_id: int) -> dict:
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")
    peers_result = await db.execute(
        select(Product).where(
            Product.origin_country == product.origin_country,
            Product.id != product.id,
            Product.is_active == True
        ).limit(5)
    )
    peers = peers_result.scalars().all()
    return {
        "product": {"sku": product.sku, "name": product.name,
                    "origin": product.origin_country, "producer": product.producer_name},
        "peers": [{"sku": p.sku, "name": p.name, "producer": p.producer_name,
                   "origin": p.origin_country} for p in peers],
    }
