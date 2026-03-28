from fastapi import FastAPI

from server import __version__

app = FastAPI(title="iron-counsil-server", version=__version__)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": app.title,
        "status": "ok",
        "version": app.version,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
