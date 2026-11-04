"""Trusted M3A fixture: averaging an empty collection divides by zero."""


def average(values):
    return sum(values) / len(values)
