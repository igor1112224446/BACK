"""
Example of how to use the form filling API.

This script demonstrates:
1. Creating a form application with field mappings
2. Filling out a form with product data
3. Retrieving submission results
"""

import requests
import json
from typing import Any

# API configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "change-me"  # Update this to match BOT_API_KEY in .env

headers = {"Authorization": f"Bearer {API_KEY}"}


def create_form_application(retailer_name: str, form_url: str, field_mappings: list[dict[str, Any]]) -> dict:
    """Create a new form application with field mappings."""
    payload = {
        "retailer_name": retailer_name,
        "form_url": form_url,
        "form_name": f"{retailer_name} Procurement Form",
        "field_mappings": field_mappings,
    }

    response = requests.post(f"{API_BASE_URL}/api/forms", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def fill_form(application_id: int, product_data: dict[str, Any]) -> dict:
    """Fill out a form with product data."""
    payload = {
        "application_id": application_id,
        "product_data": product_data,
    }

    response = requests.post(f"{API_BASE_URL}/api/forms/fill", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def get_submission(submission_id: int) -> dict:
    """Get submission details."""
    response = requests.get(f"{API_BASE_URL}/api/forms/submission/{submission_id}", headers=headers)
    response.raise_for_status()
    return response.json()


def list_forms(retailer_name: str | None = None) -> list:
    """List all available form applications."""
    params = {}
    if retailer_name:
        params["retailer_name"] = retailer_name

    response = requests.get(f"{API_BASE_URL}/api/forms", params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    print("=== Form Filling API Example ===\n")

    # Example 1: Create a form application
    print("1. Creating form application for Yarche supermarket...")
    field_mappings = [
        {
            "field_name": "product_name",
            "field_type": "text",
            "product_field": "name",
            "xpath": "//input[@name='product_name']",
            "required": True,
        },
        {
            "field_name": "product_description",
            "field_type": "textarea",
            "product_field": "description",
            "css_selector": "textarea[name='description']",
            "required": False,
        },
        {
            "field_name": "category",
            "field_type": "select",
            "product_field": "category",
            "xpath": "//select[@name='category']",
            "required": True,
        },
        {
            "field_name": "price",
            "field_type": "number",
            "product_field": "price",
            "xpath": "//input[@name='price']",
            "required": True,
        },
        {
            "field_name": "quantity",
            "field_type": "integer",
            "product_field": "quantity",
            "xpath": "//input[@name='quantity']",
            "required": False,
        },
        {
            "field_name": "delivery_date",
            "field_type": "date",
            "product_field": "delivery_date",
            "xpath": "//input[@name='delivery_date']",
            "required": True,
        },
        {
            "field_name": "supplier",
            "field_type": "text",
            "product_field": "supplier",
            "xpath": "//input[@name='supplier']",
            "required": False,
        },
    ]

    form_app = create_form_application(
        retailer_name="Yarche",
        form_url="https://zakupkiyarche.ru/form/details",
        field_mappings=field_mappings,
    )
    print(f"✓ Form created with ID: {form_app['id']}\n")

    # Example 2: Fill form with product data
    print("2. Filling form with product data...")
    product_data = {
        "name": "Organic Buckwheat",
        "description": "Premium quality organic buckwheat from local farms",
        "category": "Grains & Cereals",
        "price": 450.50,
        "quantity": 100,
        "unit": "kg",
        "supplier": "FarmersCoop LLC",
        "delivery_date": "2026-10-15",
        "specifications": {
            "origin": "Russia",
            "shelf_life_months": 12,
            "certification": "GOST R 52349-2005",
        },
    }

    fill_result = fill_form(form_app["id"], product_data)
    print(f"✓ Form submission ID: {fill_result['submission_id']}")
    print(f"✓ Status: {'Successful' if fill_result['ok'] else 'Failed'}")

    if fill_result.get("errors"):
        print(f"✗ Errors: {fill_result['errors']}")
    else:
        print(f"✓ All fields filled successfully")

    if fill_result.get("filled_data"):
        print(f"\nFilled fields:")
        for key, value in fill_result["filled_data"].items():
            print(f"  - {key}: {value}")
    print()

    # Example 3: Get submission details
    print("3. Retrieving submission details...")
    submission = get_submission(fill_result["submission_id"])
    print(f"Submission ID: {submission['id']}")
    print(f"Status: {submission['status']}")
    print(f"Created: {submission['created_at']}")
    if submission.get("error_message"):
        print(f"Errors: {submission['error_message']}")
    print()

    # Example 4: List all forms for a retailer
    print("4. Listing forms for Yarche...")
    forms = list_forms("Yarche")
    for form in forms:
        print(f"  - {form['retailer_name']}: {form['form_url']} (ID: {form['id']})")


if __name__ == "__main__":
    main()
