import ftplib
import os
import xml.etree.ElementTree as ET
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone


# Constants
FTP_HOST = "ftp.bom.gov.au"
FTP_DIR = "/anon/gen/fwo/"
FILENAME = "IDT12329.xml"
LOCATION = "Far North West Coast: Sandy Cape to Stanley"

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


def get_issue_descriptor(issue_time_str):
    # Strip the colon in timezone offset for strptime compatibility
    if issue_time_str[-3] == ":":
        issue_time_str = issue_time_str[:-3] + issue_time_str[-2:]
    dt = datetime.strptime(issue_time_str, "%Y-%m-%dT%H:%M:%S%z")

    local_time = dt.strftime("%A")
    hour = dt.hour

    if 5 <= hour < 12:
        part_of_day = "morning"
    elif 12 <= hour < 17:
        part_of_day = "afternoon"
    elif 17 <= hour < 21:
        part_of_day = "evening"
    else:
        part_of_day = "night"

    time_formatted = dt.strftime("%-I:%M%p").lower()
    return f"Issued {local_time} {part_of_day} at {time_formatted}."


# This parses the XML and returns forecast for the west coast
def parse_forecast(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    now = datetime.now(timezone.utc).astimezone()
    forecast_lines = []

    # Extract issue time from <amoc>
    amoc = root.find("amoc")
    if amoc is not None:
        issue_time_local = amoc.findtext("issue-time-local")
        if issue_time_local:
            issue_descriptor = get_issue_descriptor(issue_time_local)
            logger.info(f"Issue time descriptor: {issue_descriptor}")
            forecast_lines.append(issue_descriptor)
            forecast_lines.append("")

    # find synoptic summary
    for area in root.findall(".//area"):
        if area.attrib.get("description") == "Tasmania":
            forecast_period = area.find("forecast-period")
            if forecast_period is not None:
                for t in forecast_period.findall("text"):
                    if t.attrib.get("type") == "synoptic_situation":
                        synoptic_text = (t.text or "").strip()
                        if synoptic_text:
                            logger.info(f"Found synoptic situation: {synoptic_text}")
                            forecast_lines.append("Weather Situation:")
                            forecast_lines.append(synoptic_text)
                            forecast_lines.append("")
            break

    # Look for warning-summary anywhere in document
    warning = root.find(".//warning-summary")
    if warning is not None and warning.text and warning.text.strip():
        warning_text = warning.text.strip()
        logger.info(f"Found warning-summary: {warning_text}")
        forecast_lines.append(f"Warning Summary: {warning_text}.")
        forecast_lines.append("")

    for area in root.findall(".//area"):
        desc = area.attrib.get("description", "").strip()
        if desc == LOCATION:
            logger.info(f"Found forecast area: {LOCATION}")

            forecast_periods = area.findall("forecast-period")
            logger.info(f"Total forecast-periods found: {len(forecast_periods)}")

            for period in forecast_periods:
                start_time_str = period.attrib.get("start-time-local", "").strip()
                try:
                    start_time = datetime.strptime(
                        start_time_str, "%Y-%m-%dT%H:%M:%S%z"
                    )
                except ValueError:
                    logger.warning(
                        f"Could not parse start-time-local: {start_time_str}"
                    )
                    continue

                logger.info(
                    f"Checking forecast-period with start-time-local={start_time_str}"
                )

                if forecast_periods:
                    first_period = forecast_periods[0]
                    start_time_str = first_period.attrib.get(
                        "start-time-local", ""
                    ).strip()
                    try:
                        start_time = datetime.strptime(
                            start_time_str, "%Y-%m-%dT%H:%M:%S%z"
                        )
                    except ValueError:
                        logger.warning(
                            f"Could not parse start-time-local: {start_time_str}"
                        )
                        return None

                    logger.info(
                        f"Using forecast-period with start-time-local={start_time_str}"
                    )

                    for t in first_period.findall("text"):
                        t_type = t.attrib.get("type", "")
                        t_value = (t.text or "").strip()
                        if t_value:
                            readable_label = t_type.replace("_", " ")
                            logger.info(f"Found text: {t_value}")
                            line = f"{readable_label}: {t_value}"
                            forecast_lines.append(line)

                    logger.info("Successfully extracted forecast.")
                    return "\n".join(forecast_lines)

            logger.info(
                f"'{LOCATION}' area found but no forecast-period with future start-time-local"
            )
            return None

    logger.info(f"Area with description='{LOCATION}' not found in XML")
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
