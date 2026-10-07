"""
Service for filling Excel-based application forms for Russian retail networks.
Supports supplier questionnaires, product information tables, and complex nested data.
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import openpyxl
from openpyxl.utils import get_column_letter


class ExcelFormFiller:
    """Fills Excel forms with supplier and product data."""

    def __init__(self, excel_bytes: bytes):
        """Initialize with Excel file bytes."""
        self.workbook = openpyxl.load_workbook(BytesIO(excel_bytes))
        self.filled_cells: dict[str, Any] = {}
        self.errors: list[str] = []

    def fill_supplier_info(self, supplier_data: dict[str, Any]) -> None:
        """Fill supplier information section."""
        ws = self.workbook.active

        mappings = {
            "supplier_name": ("A2", "B2"),
            "address": ("A3", "B3"),
            "commodity_group": ("A4", "B4"),
            "egais": ("A5", "B5"),
            "mercury_fgis": ("A6", "B6"),
            "mercury_edi": ("A7", "B7"),
            "sigais": ("A8", "B8"),
            "status": ("A9", "B9"),
            "vat_payer": ("A10", "B10"),
            "edi_work": ("A11", "B11"),
            "registration_date": ("A12", "B12"),
            "expected_sales": ("A13", "B13"),
            "competitor_presence": ("A14", "B14"),
            "product_analogues": ("A15", "B15"),
            "website": ("A16", "B16"),
            "contact_name": ("A18", "B18"),
            "contact_email": ("A19", "B19"),
            "contact_phone": ("A20", "B20"),
        }

        for field_key, (label_cell, value_cell) in mappings.items():
            if field_key in supplier_data:
                value = supplier_data[field_key]
                ws[value_cell].value = value
                self.filled_cells[value_cell] = value

    def fill_products_table(self, products: list[dict[str, Any]]) -> None:
        """Fill product information table starting from row 22."""
        ws = self.workbook.active

        # Column mapping for product table
        columns = {
            "name": "A",
            "barcode": "B",
            "unit": "D",
            "price_without_vat": "E",
            "price_with_vat": "F",
            "vat_rate": "G",
            "recommended_price": "H",
            "markup_percent": "J",
            "sales_rating": "K",
            "product_turnover": "L",
            "shelf_life": "M",
            "monitoring_ok": "N",
            "monitoring_auchan": "O",
            "monitoring_baton": "P",
            "monitoring_magnit": "Q",
            "monitoring_lenta": "R",
            "monitoring_krasnyi_yar": "S",
            "photo": "T",
            "certificate": "U",
        }

        start_row = 23  # Products start from row 23
        for product_idx, product in enumerate(products):
            row = start_row + product_idx
            for field_key, col_letter in columns.items():
                if field_key in product:
                    cell_ref = f"{col_letter}{row}"
                    ws[cell_ref].value = product[field_key]
                    self.filled_cells[cell_ref] = product[field_key]

    def save(self) -> bytes:
        """Save workbook to bytes."""
        output = BytesIO()
        self.workbook.save(output)
        output.seek(0)
        return output.getvalue()

    def get_filled_cells_summary(self) -> dict[str, Any]:
        """Get summary of filled cells."""
        return {
            "total_filled": len(self.filled_cells),
            "cells": self.filled_cells,
            "errors": self.errors,
        }


def create_default_supplier_questionnaire() -> bytes:
    """Create a default supplier questionnaire template."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Questionnaire"

    # Header
    ws["A1"].value = "Анкета Контрагента"
    ws["A1"].font = openpyxl.styles.Font(bold=True, size=14)

    # Supplier section
    supplier_section = [
        ("Поставщик", "поле свободное для заполнения"),
        ("Фактический адрес:", "поле свободное для заполнения"),
        ("Группа товаров:", "поле свободное для заполнения"),
        ("ЕГАИС", "НЕТ"),
        ("ФГИС Меркурий", "ДА"),
        ("Интеграция EDI-Меркурий", "ДА"),
        ("СИГАИС", "НЕТ"),
        ("Статус", "Производитель"),
        ("Плательщик НДС", "ДА"),
        ("Работа по EDI", "НЕТ"),
        ("Дата регистрации предприятия", "поле свободное для заполнения"),
        ("Предполагаемые продажи в мес с 1 ТТ", "поле свободное для заполнения"),
        ("Представленность в сетях конкурентах", "поле свободное для заполнения"),
        ("Аналоги продукции на рынке", "поле свободное для заполнения"),
        ("Ссылка на сайт", "поле свободное для заполнения"),
    ]

    row = 2
    for label, placeholder in supplier_section:
        ws[f"A{row}"].value = label
        ws[f"B{row}"].value = placeholder
        ws[f"A{row}"].font = openpyxl.styles.Font(bold=True)
        row += 1

    # Contact section
    ws[f"A{row}"].value = "Контакты:"
    ws[f"A{row}"].font = openpyxl.styles.Font(bold=True)
    row += 1

    contact_fields = [
        ("ФИО/должность", "поле свободное для заполнения"),
        ("E-mail :", "поле свободное для заполнения"),
        ("№ телефона", "поле свободное для заполнения"),
    ]

    for label, placeholder in contact_fields:
        ws[f"A{row}"].value = label
        ws[f"B{row}"].value = placeholder
        ws[f"A{row}"].font = openpyxl.styles.Font(bold=True)
        row += 1

    # Product table header
    row = 22
    ws[f"A{row}"].value = "Наименование"
    ws[f"B{row}"].value = "Штрих-код"
    ws[f"D{row}"].value = "Базовая ед. измер. (шт/кг/л)"
    ws[f"E{row}"].value = "Цена поставки БЕЗ НДС"
    ws[f"F{row}"].value = "Цена поставки с НДС"
    ws[f"G{row}"].value = "Ставка НДС"
    ws[f"H{row}"].value = "Рекомендованная розничная цена"
    ws[f"J{row}"].value = "% наценки, min/max"
    ws[f"K{row}"].value = "Место в рейтинге продаж"
    ws[f"L{row}"].value = "Планируемый Товарооборот"
    ws[f"M{row}"].value = "Срок годности товара"
    ws[f"N{row}"].value = "Мониторинг Окей"
    ws[f"O{row}"].value = "Мониторинг Ашан"
    ws[f"P{row}"].value = "Мониторинг Батон"
    ws[f"Q{row}"].value = "Мониторинг Магнит"
    ws[f"R{row}"].value = "Мониторинг ЛЕНТА"
    ws[f"S{row}"].value = "Мониторинг Красный ЯР"
    ws[f"T{row}"].value = "Фото"
    ws[f"U{row}"].value = "Сертификат"

    # Style header
    for col in range(1, 22):
        ws.cell(row=row, column=col).font = openpyxl.styles.Font(bold=True)

    # Adjust column widths
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 15
    ws.column_dimensions["G"].width = 12
    ws.column_dimensions["H"].width = 18

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
