import logging
from fastapi import FastAPI
from reader import Reader, SERIAL_PORT, BAUD_RATE

app = FastAPI()
reader = Reader(SERIAL_PORT, BAUD_RATE)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.get("/read")
def read_meter():
    logger.debug("Reading meter...")
    return reader.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)