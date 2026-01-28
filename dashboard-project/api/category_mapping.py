# Category Mapping - Complete Reference
# Maps Excel category names to ProductCat IDs and all Product IDs from CRM
# Based on user-provided tables

CATEGORY_MAPPING = {
    'per': {  # Перчатки
        'name_ru': 'Перчатки',
        'productcat_ids': [
            '42ac50da-efa0-9baa-51cc-50efc73a1fc6',
            '3fb2004f-ffe1-67b3-d797-65aa1f509de3',
            '8d432105-5ecf-3fc7-8242-62b32dc497e8',
            'f35511c6-0a8c-6ece-02cb-62b32d67dbf4',
        ],
        'count': 914  # Products auto-calculated via productcat
    },
    'ruk': {  # Рукавицы
        'name_ru': 'Рукавицы',
        'productcat_ids': [
            '56e605af-31df-9377-5322-50f0124b66d1',
        ],
        'product_ids': [  # Additional products from user table
            'd2ce11bf-8b1d-f983-8bda-50f01578752c',
            'f475045f-b2ac-7a7d-cce6-5296ed1df430',
            '10cf1f0e-1d53-1707-a72f-5c766eec4b8d',
            '8e93811a-e6e9-e8be-712d-50f01412e6db',
            'a498009d-eb1b-618e-6b03-57442be792cf',
            'b1ca376a-d940-3eb7-1b82-50f0186322bf',
            '59ddf14a-7906-44e9-bf05-580f265bd891',
            '98b5c6ff-d833-861d-fe10-5178edc2bfb4',
            'de48d2c0-42c0-9f4c-2113-5a7d5e017e72',
            'eeef745f-89bb-7b77-aaaf-5443d6fba3e0',
            'ee493828-89d0-5092-f050-5a0e9c845025',
            '922b2ad9-ca81-d4c7-3a88-5a1ea4e4a340',
            '616c84e6-dcac-de58-9b8a-54e0c86d01d5',
            'b763d802-6535-6073-4bd0-5672c1dfb4bb',
            'd201cc4d-f52d-3a85-e595-5a1295f28df7',
            'b4dcac13-b7dd-7b1c-91ce-50f017f3ba80',
        ],
        'count': 127
    },
    'vaf': {  # Вафля
        'name_ru': 'Вафля',
        'productcat_ids': [
            '74bf507d-a38e-ea92-6d81-626a9915ed7d',
        ],
        'count': 66
    },
    'obliv': {  # Облив
        'name_ru': 'Облив',
        'productcat_ids': [
            'b7ece599-c211-52fd-2f30-5c21f1a851ca',
            'bf4581e7-681a-75ce-2796-62baa764dcf7',
            'd716ff1c-96e4-3451-f8a8-50efe14e851e',
        ],
        'count': 181
    },
    'vetosh': {  # Ветошь
        'name_ru': 'Ветошь',
        'productcat_ids': [
            'c5d5d05c-a672-08bb-5f3b-59cb95299ef3',
            '5ddd11ee-f0fe-39b3-8483-6613bc528163',
            'aaa602e1-a42d-5972-7830-6736fd16cef1',
        ],
        'product_ids': [  # Additional products from user table
            'cdcf27ae-b7cd-38e6-14f0-50f003593239',
            '796c7093-cf5c-ffbc-3bae-56727abe0964',
        ],
        'count': 32
    },
    'stretch': {  # Стретч
        'name_ru': 'Стретч',
        'productcat_ids': [
            'd2ca8d1d-e078-4276-c733-5488539d35e6',
            'ad0cafb2-82e3-bd9f-7de8-643e911e5bff',
            '2764ae01-c9f7-7b3e-78f4-643e91aafa06',
        ],
        'product_ids': [  # Additional products from user table
            'e11ff355-c7f2-4c90-b584-5256604b4b04',
            '88538027-50db-3dd0-e0da-5f28053e57ad',
            'cbeaa605-185a-6c4a-767f-6053554e8675',
            'de2d057b-b351-fe7c-20a0-63db822cfeac',
            'eee460cb-7983-7d33-d4ec-625fc34b74bc',
        ],
        'count': 17
    },
    'bugs': {  # Мешки
        'name_ru': 'Мешки',
        'productcat_ids': [
            'e0fcedd5-485c-e14d-9a80-54885389b508',
        ],
        'count': 12
    },
    'china': {  # Китайские перчатки
        'name_ru': 'Китайские перчатки',
        'productcat_ids': [
            '5502e046-af74-daca-00cc-67f7c90060d0',
        ],
        'count': 32
    },
}


def get_productcat_ids(category_key: str) -> list:
    """Get ProductCat IDs for a category."""
    return CATEGORY_MAPPING.get(category_key, {}).get('productcat_ids', [])


def get_product_ids(category_key: str) -> list:
    """Get additional Product IDs for a category."""
    return CATEGORY_MAPPING.get(category_key, {}).get('product_ids', [])


def build_sql_condition(category_key: str) -> str:
    """Build SQL WHERE condition for a category."""
    data = CATEGORY_MAPPING.get(category_key)
    if not data:
        return "1=0"
    
    cat_ids = data.get('productcat_ids', [])
    prod_ids = data.get('product_ids', [])
    
    parts = []
    if cat_ids:
        cat_str = ",".join([f"'{c}'" for c in cat_ids])
        parts.append(f"(productcat.id IN ({cat_str}) OR productcat.parent_category_id IN ({cat_str}))")
    if prod_ids:
        prod_str = ",".join([f"'{p}'" for p in prod_ids])
        parts.append(f"product.id IN ({prod_str})")
    
    return " OR ".join(parts) if parts else "1=0"


def get_all_categories() -> list:
    """Get list of all category keys."""
    return list(CATEGORY_MAPPING.keys())


# Excel to internal key mapping
EXCEL_TO_KEY = {
    'НАШ ТОВАР': 'own_prod',
    'ПЕРЧАТКИ': 'per',
    'ПЕРЕКУП': 'resale',
    'ОБЛИВ': 'obliv',
    'ВАФЛЯ': 'vaf',
    'ВЕТОШЬ': 'vetosh',
    'РУКАВИЦЫ': 'ruk',
    'СТРЕТЧ': 'stretch',
    'МЕШКИ': 'bugs',
    'КИТАЙСКИЕ ПЕРЧАТКИ': 'china',
}

def determine_category(row: dict) -> str:
    """
    Determine internal category key based on product properties.
    Check priority:
    1. Resale (own_prod == 0) -> 'resale'
    2. Specific Product ID match
    3. Category ID or Parent Category ID match
    """
    product_id = row.get('product_id')
    cat_id = row.get('cat_id')
    parent_cat_id = row.get('parent_cat_id')
    own_prod = row.get('own_prod')
    
    # Check resale first (own_prod = 0)
    # Note: In database own_prod is 1 for True, 0 for False.
    if own_prod == 0:
        return 'resale'
    
    # Check each category from the mapping
    for cat_key, cat_data in CATEGORY_MAPPING.items():
        productcat_ids = cat_data.get('productcat_ids', [])
        product_ids = cat_data.get('product_ids', [])
        
        # Check if product_id is in explicit product_ids
        if product_ids and product_id in product_ids:
            return cat_key
        
        # Check if cat_id or parent_cat_id matches productcat_ids
        if cat_id in productcat_ids or parent_cat_id in productcat_ids:
            return cat_key
    
    return None
