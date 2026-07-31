"""base_schema — creates all core tables from scratch.

This is the TRUE initial migration. Every subsequent migration in the chain
assumes these tables already exist. On a fresh PostgreSQL database this
migration runs first and creates everything that the existing chain ALTERs.

Revision ID: 000000000000
Revises: (none — this is the root)
Create Date: 2026-07-31
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "000000000000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tenants ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("tier", sa.String(50), nullable=True),
        sa.Column("config_json", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("phone", sa.String(50), unique=True, nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("email_verified", sa.Boolean, default=False, server_default="false"),
        sa.Column("phone_verified", sa.Boolean, default=False, server_default="false"),
        sa.Column("totp_secret", sa.String(64), nullable=True),
        sa.Column("totp_enabled", sa.Boolean, default=False, server_default="false"),
        sa.Column("mfa_otp_token", sa.Text, nullable=True),
        sa.Column("biometric_credential_id", sa.String(255), nullable=True),
        sa.Column("biometric_public_key", sa.String(1024), nullable=True),
        sa.Column("sso_provider", sa.String(50), nullable=True),
        sa.Column("sso_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── taxonomies ────────────────────────────────────────────────────────────
    op.create_table(
        "taxonomies",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── taxonomy_nodes ───────────────────────────────────────────────────────
    op.create_table(
        "taxonomy_nodes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("taxonomy_id", sa.Integer, sa.ForeignKey("taxonomies.id"), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, default=0, server_default="0"),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── taxonomy_items ───────────────────────────────────────────────────────
    op.create_table(
        "taxonomy_items",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("node_id", sa.Integer, sa.ForeignKey("taxonomy_nodes.id"), nullable=False),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("code", sa.String(100), unique=True, nullable=False),
        sa.Column("common_name", sa.String(255), nullable=False),
        sa.Column("scientific_name", sa.String(255), nullable=True),
        sa.Column("genre", sa.String(255), nullable=True),
        sa.Column("phylum", sa.String(255), nullable=True),
        sa.Column("tax_class", sa.String(255), nullable=True),
        sa.Column("order_name", sa.String(255), nullable=True),
        sa.Column("family", sa.String(255), nullable=True),
        sa.Column("gestation_period", sa.String(100), nullable=True),
        sa.Column("gestation_unit", sa.String(50), nullable=True),
        sa.Column("local_uses", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("qr_seed", sa.String(64), unique=True, nullable=True, index=True),
        sa.Column("nfc_uid_template", sa.String(255), nullable=True),
        sa.Column("barcode_prefix", sa.String(12), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── item_names ───────────────────────────────────────────────────────────
    op.create_table(
        "item_names",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean, default=False, server_default="false"),
    )

    # ── item_attributes ──────────────────────────────────────────────────────
    op.create_table(
        "item_attributes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("unit", sa.String(100), nullable=True),
    )

    # ── item_identifier_logs ─────────────────────────────────────────────────
    op.create_table(
        "item_identifier_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("identifier_type", sa.String(20), nullable=False),
        sa.Column("identifier_value", sa.String(255), nullable=False, index=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("metadata_json", sa.Text, nullable=True),
    )

    # ── products ─────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("sku", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("origin_country", sa.String(100), nullable=True),
        sa.Column("origin_region", sa.String(255), nullable=True),
        sa.Column("producer_id", sa.Integer, nullable=True),
        sa.Column("producer_name", sa.String(255), nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("harvest_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_requirements", sa.String(500), nullable=True),
        sa.Column("qr_code", sa.Text, nullable=True),
        sa.Column("barcode", sa.Text, nullable=True),
        sa.Column("nfc_tag_id", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── warehouses ───────────────────────────────────────────────────────────
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("capacity_items", sa.Integer, nullable=True),
        sa.Column("temperature_celsius", sa.Float, nullable=True),
        sa.Column("humidity_percent", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── batches ──────────────────────────────────────────────────────────────
    op.create_table(
        "batches",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("batch_number", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("serial_number", sa.String(255), nullable=True, index=True),
        sa.Column("manufacturer_part_number", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=True, server_default="pending"),
        sa.Column("production_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── warehouse_items ──────────────────────────────────────────────────────
    op.create_table(
        "warehouse_items",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("warehouse_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("location_zone", sa.String(100), nullable=True),
        sa.Column("location_rack", sa.String(100), nullable=True),
        sa.Column("location_bin", sa.String(100), nullable=True),
        sa.Column("last_counted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── tracking_events ──────────────────────────────────────────────────────
    op.create_table(
        "tracking_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("location_name", sa.String(255), nullable=True),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("temperature_celsius", sa.Float, nullable=True),
        sa.Column("humidity_percent", sa.Float, nullable=True),
        sa.Column("recorded_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── shipments ────────────────────────────────────────────────────────────
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("shipment_number", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("status", sa.String(30), server_default="created"),
        sa.Column("origin_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("destination_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("carrier_name", sa.String(255), nullable=True),
        sa.Column("carrier_ref", sa.String(255), nullable=True),
        sa.Column("vessel_name", sa.String(255), nullable=True),
        sa.Column("ferry_route", sa.String(255), nullable=True),
        sa.Column("courier_tracking_code", sa.String(255), nullable=True),
        sa.Column("courier_url", sa.String(500), nullable=True),
        sa.Column("estimated_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_weight_kg", sa.Float, nullable=True),
        sa.Column("total_volume_m3", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── shipment_batches ─────────────────────────────────────────────────────
    op.create_table(
        "shipment_batches",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("shipment_id", sa.Integer, sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("item_shipment_status", sa.String(20), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── shipment_tracking_events ─────────────────────────────────────────────
    op.create_table(
        "shipment_tracking_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("shipment_id", sa.Integer, sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("status", sa.String(100), nullable=False),
        sa.Column("location_name", sa.String(255), nullable=True),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("carrier_status", sa.String(255), nullable=True),
        sa.Column("estimated_next_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── traceability_events ──────────────────────────────────────────────────
    op.create_table(
        "traceability_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("event_id", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("location_name", sa.String(255), nullable=True),
        sa.Column("location_lat", sa.Float, nullable=True),
        sa.Column("location_lng", sa.Float, nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("handler_id", sa.Integer, nullable=False),
        sa.Column("handler_name", sa.String(255), nullable=False),
        sa.Column("handler_organization", sa.String(255), nullable=True),
        sa.Column("temperature_celsius", sa.Float, nullable=True),
        sa.Column("humidity_percent", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("attachment_urls", sa.Text, nullable=True),
        sa.Column("qr_scan_id", sa.String(100), nullable=True),
        sa.Column("nfc_scan_id", sa.String(100), nullable=True),
        sa.Column("barcode_scan", sa.String(100), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── certificates ─────────────────────────────────────────────────────────
    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("certificate_id", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("issuer_id", sa.Integer, nullable=False),
        sa.Column("issuer_name", sa.String(255), nullable=False),
        sa.Column("issuing_body", sa.String(255), nullable=True),
        sa.Column("recipient_entity", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("issued_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Integer, nullable=True),
        sa.Column("digital_signature", sa.Text, nullable=True),
        sa.Column("blockchain_hash", sa.String(255), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_certificates_expiry_date", "certificates", ["expiry_date"])

    # ── cargo_registrations ──────────────────────────────────────────────────
    op.create_table(
        "cargo_registrations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("origin_location", sa.String(255), nullable=True),
        sa.Column("destination_location", sa.String(255), nullable=True),
        sa.Column("mode", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("carrier_name", sa.String(255), nullable=True),
        sa.Column("carrier_ref", sa.String(255), nullable=True),
        sa.Column("tracking_number", sa.String(255), nullable=True),
        sa.Column("estimated_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("volume_m3", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── certificate_requests ─────────────────────────────────────────────────
    op.create_table(
        "certificate_requests",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("cargo_id", sa.Integer, sa.ForeignKey("cargo_registrations.id"), nullable=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("requested_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("applicant_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("applicant_notes", sa.Text, nullable=True),
        sa.Column("target_market", sa.String(100), nullable=True),
        sa.Column("reviewer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── collections + feed_sources ───────────────────────────────────────────
    op.create_table(
        "feed_sources",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("feed_type", sa.String(50), server_default="rss"),
        sa.Column("taxonomy_target_id", sa.Integer, sa.ForeignKey("taxonomies.id"), nullable=True),
        sa.Column("node_target_id", sa.Integer, sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("schedule_minutes", sa.Integer, server_default="1440"),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("api_key", sa.String(500), nullable=True),
        sa.Column("config_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "collections",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean, default=False, server_default="false"),
        sa.Column("feed_source_id", sa.Integer, sa.ForeignKey("feed_sources.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "collection_items",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("collection_id", sa.Integer, sa.ForeignKey("collections.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── item_rates ───────────────────────────────────────────────────────────
    op.create_table(
        "item_rates",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("origin_region", sa.String(255), nullable=False),
        sa.Column("destination_region", sa.String(255), nullable=False),
        sa.Column("mode", sa.String(50), nullable=False),
        sa.Column("carrier", sa.String(255), nullable=True),
        sa.Column("price_per_kg", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("transit_days_min", sa.Integer, nullable=True),
        sa.Column("transit_days_max", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.String(1), server_default="Y"),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── search_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "search_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("query", sa.String(500), nullable=False, index=True),
        sa.Column("result_count", sa.Integer, server_default="0"),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("user_id", sa.Integer, nullable=True, index=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("response_time_ms", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── contact_messages ─────────────────────────────────────────────────────
    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── enrichment_logs + suggestions ────────────────────────────────────────
    op.create_table(
        "enrichment_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("source", sa.String(20), nullable=True),
        sa.Column("status", sa.String(10), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("triggered_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "enrichment_suggestions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("suggestion_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("confidence", sa.String(20), server_default="medium"),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── events ───────────────────────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("secret", sa.String(128), nullable=True),
        sa.Column("events", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "event_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("channel", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.Text, nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("published_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── telemetry ────────────────────────────────────────────────────────────
    op.create_table(
        "telemetry_readings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("device_id", sa.String(100), nullable=False, index=True),
        sa.Column("telemetry_type", sa.String(50), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=True, index=True),
        sa.Column("value_float", sa.Float, nullable=True),
        sa.Column("value_str", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("location_lat", sa.Float, nullable=True),
        sa.Column("location_lng", sa.Float, nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "telemetry_alerts",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("telemetry_type", sa.String(50), nullable=False),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("threshold", sa.Float, nullable=True),
        sa.Column("actual_value", sa.Float, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), server_default="warning"),
        sa.Column("acknowledged", sa.Boolean, default=False, server_default="false"),
        sa.Column("acknowledged_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_telemetry_alerts_acknowledged", "telemetry_alerts", ["acknowledged"])

    # ── api_keys ─────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("key_prefix", sa.String(8), nullable=False, index=True),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rate_limit", sa.Integer, server_default="1000"),
        sa.Column("rate_limit_window", sa.Integer, server_default="3600"),
        sa.Column("scopes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── retention ────────────────────────────────────────────────────────────
    op.create_table(
        "archive_policies",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("archive_to_table", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── esg ──────────────────────────────────────────────────────────────────
    op.create_table(
        "item_carbon_footprints",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("kg_co2e_per_kg", sa.Float, nullable=False),
        sa.Column("water_usage_l_per_kg", sa.Float, nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("methodology", sa.String(100), nullable=True),
        sa.Column("confidence", sa.String(20), server_default="medium"),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ── recalls ──────────────────────────────────────────────────────────────
    op.create_table(
        "recalls",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=False, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=True, index=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="initiated"),
        sa.Column("affected_region", sa.String(255), nullable=True),
        sa.Column("notified_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_recalls_status", "recalls", ["status"])

    op.create_table(
        "recall_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("recall_id", sa.Integer, sa.ForeignKey("recalls.id"), nullable=False, index=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("performed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # ── suppliers ────────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("regions", sa.Text, nullable=True),
        sa.Column("certifications", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true", nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "supplier_scorecards",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.id"), nullable=False, index=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("on_time_delivery_pct", sa.Float, nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("cert_compliance_pct", sa.Float, nullable=True),
        sa.Column("audit_result", sa.String(50), nullable=True),
        sa.Column("overall_score", sa.Float, nullable=True, index=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_scorecards_supplier_score", "supplier_scorecards", ["supplier_id", "overall_score"])

    # ── insurance ────────────────────────────────────────────────────────────
    op.create_table(
        "cargo_policies",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("carrier", sa.String(255), nullable=True),
        sa.Column("policy_number", sa.String(100), nullable=False),
        sa.Column("coverage_amount", sa.Float, nullable=False),
        sa.Column("premium", sa.Float, nullable=True),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, server_default="true", nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cargo_policies_item_active", "cargo_policies", ["item_id", "is_active"])

    op.create_table(
        "insurance_claims",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("cargo_policies.id"), nullable=False, index=True),
        sa.Column("incident_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("claim_amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("documents_json", sa.JSON, nullable=True),
        sa.Column("filed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_insurance_claims_status", "insurance_claims", ["status"])

    # ── item_inventory + inventory_movements ─────────────────────────────────
    op.create_table(
        "item_inventory",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("warehouse_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("total_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("available_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reserved_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_temperature_celsius", sa.Float, nullable=True),
        sa.Column("avg_humidity_percent", sa.Float, nullable=True),
        sa.Column("last_stocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_counted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("taxonomy_items.id"), nullable=False, index=True),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=True),
        sa.Column("warehouse_id", sa.Integer, sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("reference_type", sa.String(20), nullable=True),
        sa.Column("reference_id", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("moved_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    for tbl in [
        "inventory_movements", "item_inventory",
        "insurance_claims", "cargo_policies",
        "supplier_scorecards", "suppliers",
        "recall_events", "recalls",
        "item_carbon_footprints", "archive_policies",
        "api_keys", "telemetry_alerts", "telemetry_readings",
        "event_logs", "webhook_subscriptions",
        "enrichment_suggestions", "enrichment_logs",
        "contact_messages", "search_logs", "item_rates",
        "collection_items", "collections", "feed_sources",
        "certificate_requests", "cargo_registrations",
        "certificates", "traceability_events",
        "shipment_tracking_events", "shipment_batches", "shipments",
        "tracking_events", "warehouse_items", "batches",
        "warehouses", "products",
        "item_identifier_logs", "item_attributes", "item_names",
        "taxonomy_items", "taxonomy_nodes", "taxonomies",
        "users", "tenants",
    ]:
        op.drop_table(tbl)

