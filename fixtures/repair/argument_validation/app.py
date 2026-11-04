"""Trusted M3A fixture: port parsing accepts numbers outside 1-65535."""


def parse_port(value):
    return int(value)
