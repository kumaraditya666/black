"""Trusted M3A fixture: a non-numeric argument raises the wrong exception type."""


def parse_port(value):
    try:
        return int(value)
    except TypeError:
        raise ValueError('port must be numeric')
