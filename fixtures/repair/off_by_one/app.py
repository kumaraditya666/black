"""Trusted M3A fixture: find_index scans one element past the list."""


def find_index(items, target):
    for index in range(len(items) + 1):
        if items[index] == target:
            return index
    return -1
