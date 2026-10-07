from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .models import FormApplication, FormFieldMapping, FormSubmission, RecordStatus
from .schemas import FormApplicationIn, FormFillIn, ProductData


def create_form_application(session: Session, form_data: FormApplicationIn) -> FormApplication:
    """Create a new form application with field mappings."""
    app = FormApplication(
        retailer_name=form_data.retailer_name,
        form_url=form_data.form_url,
        form_name=form_data.form_name,
        status=RecordStatus.active,
    )
    session.add(app)
    session.flush()

    for mapping in form_data.field_mappings:
        field_mapping = FormFieldMapping(
            application_id=app.id,
            field_name=mapping.field_name,
            field_type=mapping.field_type,
            product_field=mapping.product_field,
            xpath=mapping.xpath,
            css_selector=mapping.css_selector,
            required=mapping.required,
        )
        session.add(field_mapping)

    return app


def get_form_application(session: Session, app_id: int) -> FormApplication | None:
    """Get form application by ID."""
    return session.query(FormApplication).filter(FormApplication.id == app_id).first()


def fill_form(session: Session, fill_request: FormFillIn) -> FormSubmission:
    """Fill form fields with product data."""
    app = get_form_application(session, fill_request.application_id)
    if not app:
        raise ValueError(f"Application {fill_request.application_id} not found")

    product_data_dict = fill_request.product_data.model_dump(exclude_none=True)
    filled_data: dict[str, Any] = {}
    errors: list[str] = []

    for mapping in app.field_mappings:
        field_value = _get_field_value(product_data_dict, mapping.product_field)

        if field_value is not None:
            filled_data[mapping.field_name] = _convert_value(field_value, mapping.field_type)
        elif mapping.required:
            errors.append(f"Required field '{mapping.field_name}' (product field: {mapping.product_field}) not found")

    submission = FormSubmission(
        application_id=fill_request.application_id,
        product_data=json.dumps(product_data_dict),
        filled_data=json.dumps(filled_data) if filled_data else None,
        status=RecordStatus.active if not errors else RecordStatus.pending,
        error_message="; ".join(errors) if errors else None,
    )
    session.add(submission)
    return submission


def _get_field_value(data: dict[str, Any], field_path: str) -> Any:
    """Get value from nested dictionary using dot notation."""
    parts = field_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _convert_value(value: Any, field_type: str) -> Any:
    """Convert value to appropriate field type."""
    if value is None:
        return None

    if field_type == "text" or field_type == "string":
        return str(value)
    elif field_type == "number":
        try:
            return float(value) if isinstance(value, str) else value
        except (ValueError, TypeError):
            return None
    elif field_type == "integer":
        try:
            return int(value) if isinstance(value, str) else value
        except (ValueError, TypeError):
            return None
    elif field_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)
    elif field_type == "date":
        return str(value)
    elif field_type == "email":
        return str(value)
    elif field_type == "select":
        return str(value)
    elif field_type == "textarea":
        return str(value)
    else:
        return str(value)


def get_submission(session: Session, submission_id: int) -> FormSubmission | None:
    """Get form submission by ID."""
    return session.query(FormSubmission).filter(FormSubmission.id == submission_id).first()


def list_form_applications(session: Session, retailer_name: str | None = None) -> list[FormApplication]:
    """List form applications with optional filter by retailer name."""
    query = session.query(FormApplication).filter(FormApplication.status == RecordStatus.active)
    if retailer_name:
        query = query.filter(FormApplication.retailer_name.ilike(f"%{retailer_name}%"))
    return query.all()
