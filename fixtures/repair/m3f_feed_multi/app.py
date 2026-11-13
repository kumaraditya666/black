from settings import item_limit

def take(items, config):
    return items[:item_limit(config)]
