def rolling_sum(values, size):
    return [sum(values[i:i + size]) for i in range(len(values) - size + 2)]

def require_full_window(values, size):
    windows = rolling_sum(values, size)
    if any(len(values[i:i + size]) != size for i in range(len(windows))):
        raise IndexError('partial window')
    return windows
