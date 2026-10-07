"""
Example of filling Excel supplier questionnaire for Russian retail networks.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"
API_KEY = "change-me"  # Update to match BOT_API_KEY

headers = {"Authorization": f"Bearer {API_KEY}"}


def download_template():
    """Download the supplier questionnaire template."""
    print("Downloading template...")
    response = requests.get(f"{API_BASE_URL}/api/forms/excel/template", headers=headers)
    response.raise_for_status()

    with open("supplier_questionnaire_template.xlsx", "wb") as f:
        f.write(response.content)
    print("✓ Template saved to supplier_questionnaire_template.xlsx\n")


def fill_excel_form():
    """Fill Excel form with supplier and product data."""
    print("Filling Excel form with supplier and product data...\n")

    # Supplier information
    supplier_info = {
        "supplier_name": "ООО Фермерское кооперативное хозяйство 'Урожай'",
        "address": "Красноярск, пр. Мира, д. 100, офис 305",
        "commodity_group": "[26] ЗДОРОВОЕ ПИТАНИЕ",
        "egais": "НЕТ",
        "mercury_fgis": "ДА",
        "mercury_edi": "ДА",
        "sigais": "НЕТ",
        "status": "Производитель",
        "vat_payer": "ДА",
        "edi_work": "ДА",
        "registration_date": "2015-03-15",
        "expected_sales": "250000",
        "competitor_presence": "Yarche, Okey, Auchan, Lenta",
        "product_analogues": "Гречка от 'Лучше' и 'Здоровье'",
        "website": "https://urozhay-farm.ru",
        "contact_name": "Иван Петрович Сидоров / Директор",
        "contact_email": "ivan.sidorov@urozhay-farm.ru",
        "contact_phone": "+7 (999) 123-45-67",
    }

    # Products
    products = [
        {
            "name": "Гречка органическая крупа 800г",
            "barcode": "4650012345001",
            "unit": "шт",
            "price_without_vat": 288.56,
            "price_with_vat": 346.27,
            "vat_rate": 20,
            "recommended_price": 499.99,
            "markup_percent": "40-45%",
            "sales_rating": "5 из 130",
            "product_turnover": "5000 шт/месяц",
            "shelf_life": "24 месяца",
            "monitoring_ok": "ДА",
            "monitoring_auchan": "ДА",
            "monitoring_baton": "НЕТ",
            "monitoring_magnit": "ДА",
            "monitoring_lenta": "ДА",
            "monitoring_krasnyi_yar": "ДА",
            "photo": "product_photo_1.jpg",
            "certificate": "GOST_R_52349-2005.pdf",
        },
        {
            "name": "Рис басмати белый 1000г",
            "barcode": "4650012345002",
            "unit": "шт",
            "price_without_vat": 340.00,
            "price_with_vat": 408.00,
            "vat_rate": 20,
            "recommended_price": 599.99,
            "markup_percent": "45-50%",
            "sales_rating": "8 из 130",
            "product_turnover": "3500 шт/месяц",
            "shelf_life": "36 месяцев",
            "monitoring_ok": "ДА",
            "monitoring_auchan": "ДА",
            "monitoring_baton": "ДА",
            "monitoring_magnit": "ДА",
            "monitoring_lenta": "ДА",
            "monitoring_krasnyi_yar": "ДА",
            "photo": "product_photo_2.jpg",
            "certificate": "GOST_R_51167-98.pdf",
        },
        {
            "name": "Чечевица красная рассыпчатая 500г",
            "barcode": "4650012345003",
            "unit": "шт",
            "price_without_vat": 156.22,
            "price_with_vat": 187.47,
            "vat_rate": 20,
            "recommended_price": 349.99,
            "markup_percent": "80-85%",
            "sales_rating": "12 из 130",
            "product_turnover": "2000 шт/месяц",
            "shelf_life": "24 месяца",
            "monitoring_ok": "НЕТ",
            "monitoring_auchan": "ДА",
            "monitoring_baton": "НЕТ",
            "monitoring_magnit": "ДА",
            "monitoring_lenta": "НЕТ",
            "monitoring_krasnyi_yar": "НЕТ",
            "photo": "product_photo_3.jpg",
            "certificate": "GOST_R_51161-98.pdf",
        },
    ]

    payload = {
        "supplier_info": supplier_info,
        "products": products,
    }

    response = requests.post(f"{API_BASE_URL}/api/forms/excel/fill", json=payload, headers=headers)
    response.raise_for_status()
    result = response.json()

    print("✓ Excel form filled successfully!")
    print(f"  Total cells filled: {result['total_filled']}")
    print(f"  Output file: {result['file_name']}")
    if result.get("errors"):
        print(f"  Errors: {result['errors']}")
    print()

    return result


def main():
    print("=== Excel Supplier Questionnaire Filler ===\n")

    try:
        # Download template
        download_template()

        # Fill form
        fill_excel_form()

        print("Done! The form is ready for submission to Russian retail networks.")
        print("\nYou can now:")
        print("1. Download the template from /api/forms/excel/template")
        print("2. Fill it with your data using /api/forms/excel/fill")
        print("3. Submit the filled form to the retail network")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        print("\nMake sure the API is running:")
        print("  uvicorn app.api:app --reload")


if __name__ == "__main__":
    main()
