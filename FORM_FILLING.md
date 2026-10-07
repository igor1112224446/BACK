# Form Filling Service

Автоматическое заполнение форм заявок на сайтах российских торговых сетей на основе информации о продукте.

## Что это делает

Сервис позволяет:
1. **Регистрировать форменные приложения** (анкеты заявок) для различных ретейлеров
2. **Определять соответствие полей** между данными о продукте и полями формы
3. **Автоматически заполнять формы** на основе информации о продукте

## Модель данных

### FormApplication
Основная информация о форме заявки ретейлера.

```
id              - уникальный идентификатор
retailer_name   - название торговой сети (например, "Yarche")
form_url        - URL формы заявки
form_name       - название формы (опционально)
status          - статус формы (active, pending, archived)
created_at      - дата создания
updated_at      - дата последнего обновления
```

### FormFieldMapping
Соответствие между полем продукта и полем формы.

```
id              - уникальный идентификатор
application_id  - ID формы приложения
field_name      - название поля в форме
field_type      - тип поля (text, number, integer, date, select, textarea, email, boolean)
product_field   - путь поля в данных о продукте (использует точку как разделитель)
xpath           - XPath селектор для поля (опционально)
css_selector    - CSS селектор для поля (опционально)
required        - является ли поле обязательным
created_at      - дата создания
```

### FormSubmission
Запись о заполнении формы.

```
id              - уникальный идентификатор
application_id  - ID формы приложения
product_data    - данные о продукте (JSON)
filled_data     - заполненные данные для формы (JSON)
status          - статус (pending, active, archived)
error_message   - сообщения об ошибках при заполнении
created_at      - дата создания
submitted_at    - дата отправки (опционально)
```

## API Endpoints

### 1. Создание новой формы приложения

**POST** `/api/forms`

Создает новую форму заявки с полями для заполнения.

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "retailer_name": "Yarche",
  "form_url": "https://zakupkiyarche.ru/form/details",
  "form_name": "Procurement Form",
  "field_mappings": [
    {
      "field_name": "product_name",
      "field_type": "text",
      "product_field": "name",
      "xpath": "//input[@name='product_name']",
      "required": true
    },
    {
      "field_name": "category",
      "field_type": "select",
      "product_field": "category",
      "css_selector": "select[name='category']",
      "required": true
    },
    {
      "field_name": "price",
      "field_type": "number",
      "product_field": "price",
      "required": true
    }
  ]
}
```

**Ответ:**
```json
{
  "id": 1,
  "retailer_name": "Yarche",
  "form_url": "https://zakupkiyarche.ru/form/details",
  "form_name": "Procurement Form",
  "status": "active"
}
```

### 2. Получение информации о форме

**GET** `/api/forms/{form_id}`

Получает информацию о конкретной форме приложения.

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
```

**Ответ:**
```json
{
  "id": 1,
  "retailer_name": "Yarche",
  "form_url": "https://zakupkiyarche.ru/form/details",
  "form_name": "Procurement Form",
  "status": "active"
}
```

### 3. Список всех форм

**GET** `/api/forms`

Получает список всех активных форм приложений.

**Параметры запроса:**
- `retailer_name` (опционально) - фильтр по названию ретейлера (поиск по частичному совпадению)

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
```

**Ответ:**
```json
[
  {
    "id": 1,
    "retailer_name": "Yarche",
    "form_url": "https://zakupkiyarche.ru/form/details",
    "form_name": "Procurement Form",
    "status": "active"
  }
]
```

### 4. Заполнение формы данными продукта

**POST** `/api/forms/fill`

Заполняет форму данными о продукте в соответствии с определенными полями.

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "application_id": 1,
  "product_data": {
    "name": "Organic Buckwheat",
    "description": "Premium quality organic buckwheat",
    "category": "Grains & Cereals",
    "price": 450.50,
    "quantity": 100,
    "unit": "kg",
    "supplier": "FarmersCoop LLC",
    "delivery_date": "2026-10-15",
    "specifications": {
      "origin": "Russia",
      "shelf_life_months": 12
    }
  }
}
```

**Ответ:**
```json
{
  "ok": true,
  "submission_id": 42,
  "filled_data": {
    "product_name": "Organic Buckwheat",
    "category": "Grains & Cereals",
    "price": 450.50
  },
  "errors": null
}
```

### 5. Получение информации о заполнении

**GET** `/api/forms/submission/{submission_id}`

Получает детальную информацию о конкретном заполнении формы.

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
```

**Ответ:**
```json
{
  "id": 42,
  "application_id": 1,
  "status": "active",
  "product_data": {
    "name": "Organic Buckwheat",
    "description": "Premium quality organic buckwheat",
    "category": "Grains & Cereals",
    "price": 450.50,
    "quantity": 100,
    "unit": "kg",
    "supplier": "FarmersCoop LLC",
    "delivery_date": "2026-10-15"
  },
  "filled_data": {
    "product_name": "Organic Buckwheat",
    "category": "Grains & Cereals",
    "price": 450.50
  },
  "error_message": null,
  "created_at": "2026-10-07T10:30:00",
  "submitted_at": null
}
```

## Типы полей форм

Поддерживаемые типы полей и их поведение:

| Тип | Описание | Преобразование |
|-----|---------|------------------|
| `text` | Текстовое поле | Преобразуется в строку |
| `string` | Синоним `text` | Преобразуется в строку |
| `number` | Числовое поле | Преобразуется в float |
| `integer` | Целое число | Преобразуется в int |
| `boolean` | Логическое значение | true/false, "yes", "no" и т.д. |
| `date` | Дата | Сохраняется как строка |
| `email` | Email адрес | Преобразуется в строку |
| `select` | Выпадающее меню | Преобразуется в строку |
| `textarea` | Многострочный текст | Преобразуется в строку |

## Использование точечной нотации для вложенных полей

Для доступа к вложенным полям в данных о продукте используется точечная нотация:

```json
{
  "field_name": "origin",
  "field_type": "text",
  "product_field": "specifications.origin"
}
```

В этом примере будет извлечено значение `product_data.specifications.origin`.

## Пример использования

### Python

```python
import requests

API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key"
headers = {"Authorization": f"Bearer {API_KEY}"}

# 1. Создать форму
form_data = {
    "retailer_name": "Yarche",
    "form_url": "https://zakupkiyarche.ru/form/details",
    "form_name": "Procurement Form",
    "field_mappings": [
        {
            "field_name": "product_name",
            "field_type": "text",
            "product_field": "name",
            "required": True
        },
        {
            "field_name": "price",
            "field_type": "number",
            "product_field": "price",
            "required": True
        }
    ]
}

response = requests.post(
    f"{API_BASE_URL}/api/forms",
    json=form_data,
    headers=headers
)
form_app = response.json()
print(f"Form created: {form_app['id']}")

# 2. Заполнить форму
product_data = {
    "name": "Organic Buckwheat",
    "price": 450.50,
    "category": "Grains & Cereals"
}

fill_data = {
    "application_id": form_app["id"],
    "product_data": product_data
}

response = requests.post(
    f"{API_BASE_URL}/api/forms/fill",
    json=fill_data,
    headers=headers
)
result = response.json()
print(f"Submission ID: {result['submission_id']}")
print(f"Filled data: {result['filled_data']}")

# 3. Получить результаты
response = requests.get(
    f"{API_BASE_URL}/api/forms/submission/{result['submission_id']}",
    headers=headers
)
submission = response.json()
print(f"Status: {submission['status']}")
print(f"Errors: {submission['error_message']}")
```

## Запуск примера

```bash
# Убедитесь, что API запущена
uvicorn app.api:app --reload

# В отдельном терминале запустите пример
python scripts/form_fill_example.py
```

## Обработка ошибок

При заполнении формы могут возникнуть следующие ошибки:

1. **Обязательное поле не найдено** - если значение для обязательного поля не найдено в данных о продукте
2. **Приложение не найдено** - если указанный ID формы не существует
3. **Ошибка преобразования типа** - если значение невозможно преобразовать в нужный тип

Все ошибки возвращаются в поле `error_message` ответа API.

## Интеграция с существующей системой

Сервис форм интегрирован с существующей API и использует ту же систему аутентификации по ключу API (`BOT_API_KEY`).

Все данные о формах хранятся в одной базе данных с другими данными приложения.

## Развертывание

Для использования новой функции нужно:

1. Обновить базу данных (новые таблицы создадутся автоматически при запуске API)
2. Обновить переменные окружения в `.env` (если нужны)
3. Перезагрузить API сервис

На Railway или других хостингах просто переразворачиваете приложение с новым кодом.

---

## Работа с Excel формами

Сервис также поддерживает заполнение Excel форм, которые используются российскими торговыми сетями для сбора информации от поставщиков.

### Поддерживаемые данные

#### Информация о поставщике
- Название компании
- Адрес
- Группа товаров (категория)
- Системы интеграции (ЕГАИС, ФГИС Меркурий, СИГАИС, EDI)
- Статус (Производитель, Дистрибьютер, Дилер и т.д.)
- Статус плательщика НДС
- Дата регистрации
- Ожидаемые продажи
- Информация о конкурентах
- Контактная информация (ФИО, Email, Телефон)

#### Информация о товарах
Таблица с информацией о каждом товаре:
- Название товара
- Штрих-код
- Единица измерения
- Цена без НДС
- Цена с НДС
- Ставка НДС
- Рекомендованная розничная цена
- Процент наценки
- Место в рейтинге продаж
- Плановый товарооборот
- Срок годности
- Мониторинг в различных сетях (Оkay, Auchan, Baton, Magnit, Lenta, Красный Яр)
- Фото товара
- Сертификаты

### API Endpoints для Excel форм

#### 1. Получить шаблон формы

**GET** `/api/forms/excel/template`

Загружает шаблон анкеты поставщика в формате Excel.

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
```

**Ответ:** Excel файл (xlsx)

**Пример:**
```bash
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/api/forms/excel/template \
  -o supplier_questionnaire.xlsx
```

#### 2. Заполнить Excel форму

**POST** `/api/forms/excel/fill`

Заполняет Excel форму данными поставщика и товаров.

**Заголовок:**
```
Authorization: Bearer <BOT_API_KEY>
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "supplier_info": {
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
    "competitor_presence": "Yarche, Okey, Auchan",
    "product_analogues": "Гречка от 'Лучше' и 'Здоровье'",
    "website": "https://example.com",
    "contact_name": "Иван Петрович Сидоров",
    "contact_email": "ivan@example.com",
    "contact_phone": "+7 (999) 123-45-67"
  },
  "products": [
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
      "certificate": "GOST_R_52349-2005.pdf"
    }
  ]
}
```

**Ответ:**
```json
{
  "ok": true,
  "total_filled": 28,
  "file_name": "supplier_questionnaire_filled.xlsx",
  "errors": null
}
```

### Пример использования с Python

```python
import requests

API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key"
headers = {"Authorization": f"Bearer {API_KEY}"}

# 1. Скачать шаблон
response = requests.get(
    f"{API_BASE_URL}/api/forms/excel/template",
    headers=headers
)
with open("template.xlsx", "wb") as f:
    f.write(response.content)

# 2. Подготовить данные
supplier_data = {
    "supplier_name": "ООО Рога и копыта",
    "address": "Москва, ул. Тверская, 1",
    "commodity_group": "[25] ЗАВТРАКИ",
    "egais": "НЕТ",
    "mercury_fgis": "ДА",
    "mercury_edi": "ДА",
    "sigais": "НЕТ",
    "status": "Производитель",
    "vat_payer": "ДА",
    "edi_work": "ДА",
    "registration_date": "2010-06-01",
    "expected_sales": "500000",
    "competitor_presence": "Да, в 3 сетях",
    "product_analogues": "Есть 2-3 аналога",
    "website": "https://example.com",
    "contact_name": "Петр Иванов",
    "contact_email": "petrov@example.com",
    "contact_phone": "+7 (495) 123-45-67"
}

products = [
    {
        "name": "Каша гречневая быстрого приготовления",
        "barcode": "4650001234567",
        "unit": "шт",
        "price_without_vat": 45.00,
        "price_with_vat": 54.00,
        "vat_rate": 20,
        "recommended_price": 99.99,
        "markup_percent": "85%",
        "sales_rating": "10",
        "product_turnover": "10000 шт/месяц",
        "shelf_life": "18 месяцев",
        "monitoring_ok": "ДА",
        "monitoring_auchan": "ДА",
        "monitoring_baton": "ДА",
        "monitoring_magnit": "ДА",
        "monitoring_lenta": "ДА",
        "monitoring_krasnyi_yar": "НЕТ"
    }
]

# 3. Заполнить форму
response = requests.post(
    f"{API_BASE_URL}/api/forms/excel/fill",
    json={
        "supplier_info": supplier_data,
        "products": products
    },
    headers=headers
)
result = response.json()
print(f"Cells filled: {result['total_filled']}")
```

### Запуск примера

```bash
python scripts/excel_form_fill_example.py
```

Пример автоматически:
1. Скачивает шаблон формы
2. Заполняет его данными поставщика и товаров
3. Показывает результат
