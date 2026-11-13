from cleaner import parse_amount

def total(records):
    return sum(parse_amount(item) for item in records)
