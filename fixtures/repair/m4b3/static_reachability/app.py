def handle(value):
    return transform(value)


def transform(value):
    return value.strip().lower()
