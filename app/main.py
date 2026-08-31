from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(
    title="PulseTrack",
    description="Doctor-patient appointment and prescription API",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict:
    return {
        "app": "PulseTrack",
        "message": "Doctor-patient appointment and prescription API",
        "status": "ok",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "PulseTrack"}


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse("static/favicon.svg")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
