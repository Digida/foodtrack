from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.database import Base


class ItemIdentifierLog(Base):
    __tablename__ = "item_identifier_logs"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False, index=True)
    identifier_type = Column(String(20), nullable=False)
    identifier_value = Column(String(255), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    metadata_json = Column(Text, nullable=True)

    item = relationship("TaxonomyItem", back_populates="identifiers")


class Taxonomy(Base):
    __tablename__ = "taxonomies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    nodes = relationship("TaxonomyNode", back_populates="taxonomy")
    tenant = relationship("Tenant", back_populates="taxonomies")


class TaxonomyNode(Base):
    __tablename__ = "taxonomy_nodes"

    id = Column(Integer, primary_key=True, index=True)
    taxonomy_id = Column(Integer, ForeignKey("taxonomies.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    taxonomy = relationship("Taxonomy", back_populates="nodes")
    items = relationship("TaxonomyItem", back_populates="node", cascade="all, delete-orphan")
    tenant = relationship("Tenant", back_populates="taxonomy_nodes")


class TaxonomyItem(Base):
    __tablename__ = "taxonomy_items"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    code = Column(String(100), unique=True, nullable=False)
    common_name = Column(String(255), nullable=False)
    scientific_name = Column(String(255), nullable=True)
    genre = Column(String(255), nullable=True)
    phylum = Column(String(255), nullable=True)
    tax_class = Column(String(255), nullable=True)
    order_name = Column(String(255), nullable=True)
    family = Column(String(255), nullable=True)
    gestation_period = Column(String(100), nullable=True)
    gestation_unit = Column(String(50), nullable=True)
    local_uses = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    qr_seed = Column(String(64), nullable=True, unique=True, index=True)
    nfc_uid_template = Column(String(255), nullable=True)
    barcode_prefix = Column(String(12), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    node = relationship("TaxonomyNode", back_populates="items")
    names = relationship("ItemName", back_populates="item", cascade="all, delete-orphan")
    attributes = relationship("ItemAttribute", back_populates="item", cascade="all, delete-orphan")
    identifiers = relationship("ItemIdentifierLog", back_populates="item", cascade="all, delete-orphan")
    tenant = relationship("Tenant", back_populates="taxonomy_items")


class ItemName(Base):
    __tablename__ = "item_names"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False)
    language = Column(String(10), nullable=False)
    name = Column(String(255), nullable=False)
    is_primary = Column(Boolean, default=False)

    item = relationship("TaxonomyItem", back_populates="names")


class ItemAttribute(Base):
    __tablename__ = "item_attributes"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("taxonomy_items.id"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    unit = Column(String(100), nullable=True)

    item = relationship("TaxonomyItem", back_populates="attributes")
