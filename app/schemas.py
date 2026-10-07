from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from .models import RequestRole


class IngestOfferIn(BaseModel):
    role: RequestRole
    source_name: str = Field(..., max_length=100)
    source_offer_id: str = Field(..., max_length=255)
    from_city: str
    to_city: str
    travel_date: date
    weight_kg: float = Field(..., gt=0)
    description: str | None = None
    handoff_time_text: str | None = None
    handoff_location: str | None = None
    payment_instructions: str | None = None
    internal_contact_ref: str | None = None
    raw_payload: dict[str, Any] | None = None
    is_active: bool = True


class IngestOfferOut(BaseModel):
    ok: bool
    offer_id: int


class MatchView(BaseModel):
    match_id: int
    request_id: int
    offer_id: int
    role: RequestRole
    from_city: str
    to_city: str
    travel_date: date
    weight_kg: float
    description: str | None
    handoff_time_text: str | None
    handoff_location: str | None
    payment_instructions: str | None
    internal_contact_ref: str | None


class MatchResponse(BaseModel):
    ok: bool
    found: bool
    match: MatchView | None = None


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "colibri-dispatch-api"


class FormFieldMappingIn(BaseModel):
    field_name: str
    field_type: str
    product_field: str
    xpath: str | None = None
    css_selector: str | None = None
    required: bool = False


class FormApplicationIn(BaseModel):
    retailer_name: str
    form_url: str
    form_name: str | None = None
    field_mappings: list[FormFieldMappingIn]


class FormApplicationOut(BaseModel):
    id: int
    retailer_name: str
    form_url: str
    form_name: str | None
    status: str


class ProductData(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = None
    quantity: int | None = None
    unit: str | None = None
    supplier: str | None = None
    delivery_date: str | None = None
    specifications: dict[str, Any] | None = None
    raw_data: dict[str, Any] | None = None


class FormFillIn(BaseModel):
    application_id: int
    product_data: ProductData


class FormFillOut(BaseModel):
    ok: bool
    submission_id: int
    filled_data: dict[str, Any] | None = None
    errors: list[str] | None = None


class FormSubmissionView(BaseModel):
    id: int
    application_id: int
    status: str
    product_data: dict[str, Any]
    filled_data: dict[str, Any] | None
    error_message: str | None
    created_at: str
    submitted_at: str | None


class SupplierInfo(BaseModel):
    supplier_name: str | None = None
    address: str | None = None
    commodity_group: str | None = None
    egais: str | None = None
    mercury_fgis: str | None = None
    mercury_edi: str | None = None
    sigais: str | None = None
    status: str | None = None
    vat_payer: str | None = None
    edi_work: str | None = None
    registration_date: str | None = None
    expected_sales: str | None = None
    competitor_presence: str | None = None
    product_analogues: str | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class ProductInfo(BaseModel):
    name: str | None = None
    barcode: str | None = None
    unit: str | None = None
    price_without_vat: float | None = None
    price_with_vat: float | None = None
    vat_rate: float | None = None
    recommended_price: float | None = None
    markup_percent: str | None = None
    sales_rating: str | None = None
    product_turnover: str | None = None
    shelf_life: str | None = None
    monitoring_ok: str | None = None
    monitoring_auchan: str | None = None
    monitoring_baton: str | None = None
    monitoring_magnit: str | None = None
    monitoring_lenta: str | None = None
    monitoring_krasnyi_yar: str | None = None
    photo: str | None = None
    certificate: str | None = None


class ExcelFormFillIn(BaseModel):
    supplier_info: SupplierInfo
    products: list[ProductInfo]


class ExcelFormFillOut(BaseModel):
    ok: bool
    total_filled: int
    file_name: str
    errors: list[str] | None = None
