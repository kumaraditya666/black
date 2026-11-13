def calculate(value):
    return 10 / value

def relay(value):
    return calculate(value)

def run(value):
    return relay(value - 1)
