### Australian BOM Forecast Extractor

This is a basic python script that extracts the current days weather forecast from the BOM data.

This is currently set for the west coast of Tasmania.

To change this to suit a different area, change the following:

Find the file name for your required region from here: http://www.bom.gov.au/catalogue/data-feeds.shtml

Update the "FILENAME" variable with the file name from the previous step.

Update the "LOCATION" variable with the location you wish to use. Note that due to a strange way the BOM sets up their XML file only regions will work this way, if you would like to set this to a city then you will need to change the index on line 55 from "0" to "1" a per below

if period.attrib.get("index") == "0":
