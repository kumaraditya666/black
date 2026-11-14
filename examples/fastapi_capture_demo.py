"""Sample FastAPI app that reports unhandled exceptions to BLACKBOX."""
from fastapi import FastAPI

from blackbox.capture import install_blackbox

app = FastAPI(title='BLACKBOX capture demo')
install_blackbox(app)


def calculate_average(values: list[int]) -> float:
    return sum(values) / len(values)


@app.get('/health')
def health():
    return {'ok': True}


@app.get('/crash')
def crash():
    return {'average': calculate_average([])}
