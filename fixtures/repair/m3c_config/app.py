def connect_options(config):
    retries = int(config['retries'])
    return {'retries': retries, 'timeout': config.get('timeout', 5)}
