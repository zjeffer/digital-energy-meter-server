#!/usr/bin/python3

"""
This script will read data from serial connected to the digital meter P1 port

Originally created by Jens Depuydt
https://www.jensd.be
https://github.com/jensdepuydt

Adapted for use with home assistant by Tuur Vanhoutte
https://github.com/zjeffer
"""

import re
import json
import os
from dataclasses import dataclass
import traceback
import logging
import serial
import crcmod.predefined
from tabulate import tabulate

# Enable debug if needed:
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# change serial port
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
OBIS_CODES = os.path.join(os.path.dirname(__file__), "obis_codes.json")


@dataclass
class TelegramData:
    """
    Dataclass to store telegram data
    """
    description: str
    value: float
    unit: str

    def to_tuple(self) -> tuple:
        """ Returns the data as a tuple """
        return (self.description, self.value, self.unit)


class Reader:
    """
    Class to read data from the digital meter
    """

    def __init__(self, serial_port, baud_rate):
        self.ser = serial.Serial(serial_port, baud_rate, xonxoff=1)
        self.obis_codes = Reader.read_obis_codes_from_file()

    @staticmethod
    def read_obis_codes_from_file() -> dict:
        """ Reads the OBIS codes from the file """
        with open(OBIS_CODES, "r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def checkcrc(p1telegram) -> bool:
        """
        check CRC16 checksum of telegram and return False if not matching
        split telegram in contents and CRC16 checksum (format:contents!crc)
        """
        for match in re.compile(b'\r\n(?=!)').finditer(p1telegram):
            p1contents = p1telegram[:match.end() + 1]
            # CRC is in hex, so we need to make sure the format is correct
            givencrc = hex(int(p1telegram[match.end() + 1:].decode('ascii').strip(), 16))
        # calculate checksum of the contents
        calccrc = hex(crcmod.predefined.mkPredefinedCrcFun('crc16')(p1contents))
        # check if given and calculated match
        logger.debug("Given checksum: %s, Calculated checksum: %s", givencrc, calccrc)
        if givencrc != calccrc:
            logger.debug("Checksum incorrect, skipping...")
            return False
        return True

    def parsetelegramline(self, p1line: str) -> TelegramData:
        # parse a single line of the telegram and try to get relevant data from it
        unit = ""
        timestamp = ""
        logger.debug("Parsing: %s", p1line)
        # get OBIS code from line (format:OBIS(value)
        obis = p1line.split("(")[0]
        logger.debug("OBIS: %s", obis)
        # check if OBIS code is something we know and parse it
        if obis in self.obis_codes:
            # get values from line.
            # format:OBIS(value), gas: OBIS(timestamp)(value)
            values = re.findall(r'\(.*?\)', p1line)
            value = values[0][1:-1]
            # timestamp requires removal of last char
            if obis == "0-0:1.0.0" or len(values) > 1:
                value = value[:-1]
            # report of connected gas-meter...
            if len(values) > 1:
                timestamp = value
                value = values[1][1:-1]
            # serial numbers need different parsing: (hex to ascii)
            if "96.1.1" in obis:
                value = bytearray.fromhex(value).decode()
            else:
                # separate value and unit (format:value*unit)
                lvalue = value.split("*")
                value = float(lvalue[0])
                if len(lvalue) > 1:
                    unit = lvalue[1]
            # return result in tuple: description,value,unit
            logger.debug("[%s]: description:%s, value:%s, unit:%s", timestamp, self.obis_codes[obis], value, unit)
            return TelegramData(self.obis_codes[obis]["name"], value, unit)
        return ()

    def continuous_read(self, serial_port, baud_rate):
        """ function that reads the data every second """
        ser = serial.Serial(serial_port, baud_rate, xonxoff=1)
        p1telegram = bytearray()
        while True:
            try:
                # read input from serial port
                p1line = ser.readline()
                logger.trace("Reading: ", p1line.strip())
                # P1 telegram starts with /
                # We need to create a new empty telegram
                if "/" in p1line.decode('ascii'):
                    logger.trace("Found beginning of P1 telegram")
                    p1telegram = bytearray()
                    logger.trace('*' * 60 + "\n")
                # add line to complete telegram
                p1telegram.extend(p1line)
                # P1 telegram ends with ! + CRC16 checksum
                if "!" in p1line.decode('ascii'):
                    logger.trace("Found end")
                    logger.trace(f"\
                        {('*' * 40)}\n\
                        {p1telegram.decode('ascii').strip()}\n\
                        {('*' * 40)}")
                    if Reader.checkcrc(p1telegram):
                        # parse telegram contents, line by line
                        output = []
                        for line in p1telegram.split(b'\r\n'):
                            data = self.parsetelegramline(line.decode('ascii'))
                            if data:
                                output.append(data.to_tuple())
                                logger.debug("desc:%s, val:%s, u:%s", data.description, data.value, data.unit)
                        print(tabulate(output,
                                       headers=['Description', 'Value', 'Unit'],
                                       tablefmt='github'))
            except KeyboardInterrupt:
                logger.info("Stopping")
                ser.close()
                break
            except Exception:
                logger.error(traceback.format_exc())
                logger.error("Something went wrong...")
                ser.close()
            # flush the buffer
            ser.flush()

    def read(self) -> dict[str, tuple]:
        """
        Reads one telegram from the serial port and returns the data
        Format: dict of {description: (value, unit)}
        """
        p1line = self.ser.readline()
        p1telegram = bytearray()
        data = {}
        while True:
            p1line = self.ser.readline()
            decoded_line = p1line
            if b'/' in decoded_line:
                # P1 telegram starts with /, so create a new telegram
                p1telegram = bytearray()
            p1telegram.extend(p1line)
            if b'!' in decoded_line:
                if Reader.checkcrc(p1telegram):
                    for line in p1telegram.split(b'\r\n'):
                        if r := self.parsetelegramline(line.decode('ascii')):
                            data[r.description] = {
                                "value": r.value,
                                "unit": r.unit
                            }
                    break
        return data


def main():
    """ Run this file to continuously read the serial port """
    reader = Reader(SERIAL_PORT, BAUD_RATE)
    reader.continuous_read(SERIAL_PORT, BAUD_RATE)


if __name__ == '__main__':
    main()
