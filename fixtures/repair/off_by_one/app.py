"""Trusted M3A fixture: last_n returns one item too many."""


def last_n(items, count):
    return items[-count - 1:]
