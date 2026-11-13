from limits import limit

def select(items, config):
    return items[:limit(config)]
