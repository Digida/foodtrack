from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    tier = Column(String(50), nullable=True)
    config_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="tenant")
    certificates = relationship("Certificate", back_populates="tenant")
    batches = relationship("Batch", back_populates="tenant")
    shipments = relationship("Shipment", back_populates="tenant")
    collections = relationship("Collection", back_populates="tenant")
    cargo_registrations = relationship("CargoRegistration", back_populates="tenant")
    item_rates = relationship("ItemRate", back_populates="tenant")
    inventory_records = relationship("ItemInventory", back_populates="tenant")
    warehouses = relationship("Warehouse", back_populates="tenant")
    taxonomies = relationship("Taxonomy", back_populates="tenant")
    taxonomy_nodes = relationship("TaxonomyNode", back_populates="tenant")
    taxonomy_items = relationship("TaxonomyItem", back_populates="tenant")
    products = relationship("Product", back_populates="tenant")
    enrichment_logs = relationship("EnrichmentLog", back_populates="tenant")
    enrichment_suggestions = relationship("EnrichmentSuggestion", back_populates="tenant")
    webhook_subscriptions = relationship("WebhookSubscription", back_populates="tenant")
    event_logs = relationship("EventLog", back_populates="tenant")
    telemetry_readings = relationship("TelemetryReading", back_populates="tenant")
    telemetry_alerts = relationship("TelemetryAlert", back_populates="tenant")
    api_keys = relationship("ApiKey", back_populates="tenant")
    archive_policies = relationship("ArchivePolicy", back_populates="tenant")
    carbon_footprints = relationship("ItemCarbonFootprint", back_populates="tenant")
    recalls = relationship("Recall", back_populates="tenant")
    suppliers = relationship("Supplier", back_populates="tenant")
    supplier_scorecards = relationship("SupplierScorecard", back_populates="tenant")
    cargo_policies = relationship("CargoPolicy", back_populates="tenant")
    insurance_claims = relationship("InsuranceClaim", back_populates="tenant")
