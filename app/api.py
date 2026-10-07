from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .excel_form_service import ExcelFormFiller, create_default_supplier_questionnaire
from .form_service import create_form_application, fill_form, get_form_application, get_submission, list_form_applications
from .schemas import (
    HealthResponse,
    IngestOfferIn,
    IngestOfferOut,
    MatchResponse,
    FormApplicationIn,
    FormApplicationOut,
    FormFillIn,
    FormFillOut,
    FormSubmissionView,
    ExcelFormFillIn,
    ExcelFormFillOut,
)
from .services import init_db, to_match_view, try_match_offer_against_pending_requests, try_match_request, upsert_parsed_offer


app = FastAPI(title="Colibri Dispatch API")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.bot_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/ingest/offer", response_model=IngestOfferOut, dependencies=[Depends(require_api_key)])
def ingest_offer(payload: IngestOfferIn, session: Session = Depends(db_session)) -> IngestOfferOut:
    offer = upsert_parsed_offer(session, payload)
    try_match_offer_against_pending_requests(session, offer.id)
    return IngestOfferOut(ok=True, offer_id=offer.id)


@app.post("/api/match/request/{request_id}", response_model=MatchResponse, dependencies=[Depends(require_api_key)])
def match_request(request_id: int, session: Session = Depends(db_session)) -> MatchResponse:
    match = try_match_request(session, request_id)
    if not match:
        return MatchResponse(ok=True, found=False, match=None)
    return MatchResponse(ok=True, found=True, match=to_match_view(match))


@app.post("/api/forms", response_model=FormApplicationOut, dependencies=[Depends(require_api_key)])
def create_form(form_data: FormApplicationIn, session: Session = Depends(db_session)) -> FormApplicationOut:
    """Create a new form application with field mappings."""
    app = create_form_application(session, form_data)
    return FormApplicationOut(
        id=app.id,
        retailer_name=app.retailer_name,
        form_url=app.form_url,
        form_name=app.form_name,
        status=app.status.value,
    )


@app.get("/api/forms/{form_id}", response_model=FormApplicationOut, dependencies=[Depends(require_api_key)])
def get_form(form_id: int, session: Session = Depends(db_session)) -> FormApplicationOut:
    """Get form application details."""
    app = get_form_application(session, form_id)
    if not app:
        raise HTTPException(status_code=404, detail="Form not found")
    return FormApplicationOut(
        id=app.id,
        retailer_name=app.retailer_name,
        form_url=app.form_url,
        form_name=app.form_name,
        status=app.status.value,
    )


@app.get("/api/forms", dependencies=[Depends(require_api_key)])
def list_forms(retailer_name: str | None = None, session: Session = Depends(db_session)) -> list[FormApplicationOut]:
    """List all active form applications."""
    apps = list_form_applications(session, retailer_name)
    return [
        FormApplicationOut(
            id=app.id,
            retailer_name=app.retailer_name,
            form_url=app.form_url,
            form_name=app.form_name,
            status=app.status.value,
        )
        for app in apps
    ]


@app.post("/api/forms/fill", response_model=FormFillOut, dependencies=[Depends(require_api_key)])
def fill_application_form(fill_request: FormFillIn, session: Session = Depends(db_session)) -> FormFillOut:
    """Fill form fields with product data."""
    try:
        submission = fill_form(session, fill_request)
        filled_data = None
        errors = None

        if submission.filled_data:
            import json

            filled_data = json.loads(submission.filled_data)

        if submission.error_message:
            errors = submission.error_message.split("; ")

        return FormFillOut(
            ok=True,
            submission_id=submission.id,
            filled_data=filled_data,
            errors=errors,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/forms/submission/{submission_id}", response_model=FormSubmissionView, dependencies=[Depends(require_api_key)])
def get_form_submission(submission_id: int, session: Session = Depends(db_session)) -> FormSubmissionView:
    """Get form submission details."""
    import json

    submission = get_submission(session, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return FormSubmissionView(
        id=submission.id,
        application_id=submission.application_id,
        status=submission.status.value,
        product_data=json.loads(submission.product_data),
        filled_data=json.loads(submission.filled_data) if submission.filled_data else None,
        error_message=submission.error_message,
        created_at=submission.created_at.isoformat(),
        submitted_at=submission.submitted_at.isoformat() if submission.submitted_at else None,
    )


@app.post("/api/forms/excel/fill", response_model=ExcelFormFillOut, dependencies=[Depends(require_api_key)])
def fill_excel_form(fill_request: ExcelFormFillIn) -> ExcelFormFillOut:
    """Fill Excel supplier questionnaire with product and supplier data."""
    try:
        # Create a default supplier questionnaire
        excel_bytes = create_default_supplier_questionnaire()

        # Fill the form
        filler = ExcelFormFiller(excel_bytes)
        supplier_data = fill_request.supplier_info.model_dump(exclude_none=True)
        filler.fill_supplier_info(supplier_data)

        products_data = [product.model_dump(exclude_none=True) for product in fill_request.products]
        filler.fill_products_table(products_data)

        # Save and get summary
        filled_excel = filler.save()
        summary = filler.get_filled_cells_summary()

        return ExcelFormFillOut(
            ok=True,
            total_filled=summary["total_filled"],
            file_name="supplier_questionnaire_filled.xlsx",
            errors=summary.get("errors") if summary.get("errors") else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error filling Excel form: {str(e)}")


@app.get("/api/forms/excel/template", dependencies=[Depends(require_api_key)])
def get_excel_template() -> FileResponse:
    """Download default supplier questionnaire template."""
    import tempfile

    excel_bytes = create_default_supplier_questionnaire()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(excel_bytes)
        tmp.flush()
        return FileResponse(
            path=tmp.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="supplier_questionnaire_template.xlsx",
        )
