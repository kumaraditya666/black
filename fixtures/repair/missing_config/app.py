"""Trusted M3A fixture: a missing timeout key raises KeyError."""


def request_timeout(config):
    return config['timeout']
