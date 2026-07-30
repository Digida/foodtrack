"""SEO service — generates structured data (JSON-LD), meta tags, OG/Twitter cards."""

from typing import Any


def build_json_ld_product(product: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.get("name", ""),
        "sku": product.get("sku", ""),
        "description": product.get("description", ""),
        "category": product.get("category", ""),
        "countryOfOrigin": product.get("origin_country", ""),
        "producer": {
            "@type": "Organization",
            "name": product.get("producer_name", ""),
        },
        "weight": product.get("weight_kg"),
        "image": product.get("image_url"),
    }


def build_json_ld_taxonomy_item(item: dict) -> dict:
    ld: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Taxon",
        "name": item.get("common_name", ""),
        "scientificName": item.get("scientific_name", ""),
        "description": item.get("description", ""),
        "code": item.get("code", ""),
    }
    if item.get("phylum"):
        ld["phylum"] = item["phylum"]
    if item.get("family"):
        ld["family"] = item["family"]
    if item.get("genus"):
        ld["genus"] = item.get("genre")
    if item.get("gestation_period"):
        ld["gestationPeriod"] = f"{item['gestation_period']} {item.get('gestation_unit', '')}"
    return ld


def build_json_ld_batch(batch: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "ProductGroup",
        "name": f"Batch {batch.get('batch_number', '')}",
        "productGroupID": batch.get("batch_number", ""),
        "description": batch.get("notes", ""),
        "productionDate": batch.get("production_date"),
        "expiryDate": batch.get("expiry_date"),
        "image": batch.get("image_url"),
    }


def build_json_ld_shipment(shipment: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "ParcelDelivery",
        "trackingNumber": shipment.get("courier_tracking_code") or shipment.get("shipment_number", ""),
        "carrier": {
            "@type": "Organization",
            "name": shipment.get("carrier_name", ""),
        },
        "originAddress": {"name": shipment.get("origin_name")} if shipment.get("origin_name") else None,
        "deliveryAddress": {"name": shipment.get("destination_name")} if shipment.get("destination_name") else None,
        "expectedArrivalFrom": shipment.get("estimated_departure"),
        "expectedArrivalUntil": shipment.get("estimated_arrival"),
    }


def build_json_ld_warehouse(wh: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Warehouse",
        "name": wh.get("name", ""),
        "identifier": wh.get("code", ""),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": wh.get("address", ""),
            "addressLocality": wh.get("city", ""),
            "addressCountry": wh.get("country", ""),
        },
    }


def build_json_ld_collection(collection: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": collection.get("name", ""),
        "description": collection.get("description", ""),
        "image": collection.get("image_url"),
    }


def meta_tags(title: str, description: str, url: str, image: str | None = None) -> str:
    tags = f"""
    <title>{title}</title>
    <meta name="description" content="{description[:250]}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description[:250]}">
    <meta property="og:url" content="{url}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description[:250]}">
    """
    if image:
        tags += f'\n    <meta property="og:image" content="{image}">\n    <meta name="twitter:image" content="{image}">'
    return tags


def json_ld_script(data: dict) -> str:
    import json
    return f'<script type="application/ld+json">{json.dumps(data, default=str, ensure_ascii=False)}</script>'