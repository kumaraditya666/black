def require_entries(entries):
    if not entries:
        raise ValueError('remote service unavailable')
    return len(entries)
