"""Trusted M3A fixture: this revision already handles empty input."""


def average(values):
    if not values:
        raise ValueError('average of an empty collection')
    return sum(values) / len(values)
