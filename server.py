"""
Serves digital energy meter readings
"""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reader import Reader, SERIAL_PORT, BAUD_RATE

origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reader = Reader(SERIAL_PORT, BAUD_RATE)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

uvicorn_logger = logging.getLogger("uvicorn.error")
uvicorn_logger.setLevel(logging.DEBUG)


@app.get("/read")
def read_meter():
    """
    Reads the meter value using the reader object.
    """
    logger.debug("Reading meter...")
    return reader.read()

@app.get("/ping")
def ping():
    """
    Check if the server is alive and properly responding
    """
    logger.debug("Received a ping, responding...")
    return "pong"

@app.get("/")
def root():
    """
    Root endpoint, simply instruct the user to go to /readl
    """
    return "Go to /read to read the meter"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
