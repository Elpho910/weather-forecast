import ftplib
import os
import xml.etree.ElementTree as ET
import logging
from logging.handlers import RotatingFileHandler

# Constants
FTP_HOST = "ftp.bom.gov.au"
FTP_DIR = "/anon/gen/fwo/"
FILENAME = "IDT16000.xml"

# Set the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set input and output paths to store in same location as this script file
LOCAL_XML_PATH = os.path.join(SCRIPT_DIR, FILENAME)
OUTPUT_TXT_PATH = os.path.join(SCRIPT_DIR, "forecast.txt")

# Configure logging
LOG_PATH = os.path.join(SCRIPT_DIR, "forecast.log")
logger = logging.getLogger("ForecastLogger")
logger.setLevel(logging.INFO)

# Rotating log handler: 50 KB max per file, keep 1 backup (max 100 KB total)
handler = RotatingFileHandler(LOG_PATH, maxBytes=50_000, backupCount=1)
formatter = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# Download forecast file from BOM anonymous FTP server
def download_file_from_ftp():
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login()
        ftp.cwd(FTP_DIR)

        with open(LOCAL_XML_PATH, "wb") as f:
            ftp.retrbinary(f"RETR {FILENAME}", f.write)

    logger.info(f"Downloaded: {LOCAL_XML_PATH}")
    return LOCAL_XML_PATH


# This parses the XML and returns forecast for the west coast
def parse_forecast(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for area in root.findall(".//area"):
        desc = area.attrib.get("description", "").strip()
        if desc == "Western":
            logger.info("Found forecast area: Western")
            for period in area.findall("forecast-period"):
                if period.attrib.get("index") == "0":
                    forecast_texts = [
                        t.text.strip()
                        for t in period.findall("text")
                        if t.text and t.attrib.get("type") == "forecast"
                    ]
                    if forecast_texts:
                        return "\n".join(forecast_texts)
                    else:
                        logger.info("No forecast text found in index=0")
                        return None
            logger.info("'Western' area found but no forecast-period with index='0'")
            return None

    logger.info("Area with description='Western' not found in XML")
    return None


# XML debug for if BOM change naming standard
def debug_list_all_areas(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    print(f"Root tag is: {root.tag}")
    print("Available areas and their descriptions:")
    areas = root.findall(".//area")
    for area in areas:
        print(f" - {area.attrib.get('description', '')}")


# Saves the extracted text as forecast.txt
def save_forecast_to_txt(forecast_text):
    if forecast_text:
        with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
            f.write(forecast_text)
        logger.info(f"Forecast saved to {OUTPUT_TXT_PATH}")
    else:
        logger.info("No forecast text to save.")


def main():
    try:
        xml_path = download_file_from_ftp()
        # debug_list_all_areas(xml_path)  # uncomment to call debug
        forecast = parse_forecast(xml_path)
        save_forecast_to_txt(forecast)
    except Exception as e:
        logger.info(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
