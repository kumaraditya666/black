def parse_amount(value):
    cleaned = value.strip()
    return int(cleaned.replace(',', ''))
