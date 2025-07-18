'''
I. Fetch Process
II. Selection of Processes
III. Form

Steps:
    - Shapes Used
    - Connector Details
    - Transfer Details
    - Reuse Resources
    - Create Flow

1 Shapes Used
    - Showing a table with 
        [["Step No", "Shape Lable", "Original Type", "CPI Alternative", "Revised Sequence", "Status"]]
    - Autofilling Revised Seq
    - Shape mapping summary

    Shape-Label     = userlabel ? userlabel : name
    Original-type   = shapetype
    CPI-Alternative = shapes_mappings.get(shape_type, "NA")
    Revised-seq     = index-no
    Status          = Mapped 

2 Connector Details
    - get connector details button
    - fetching [["Type", "Action", "Id"]] 

3 Transfer Details
    - Sender and Receiver with dropdown

4 
'''

import io
import csv
import json
import xmltodict
import requests
from requests.auth import HTTPBasicAuth

# Define the shapes_mappings    
shapes_mappings = {
    "disk": "sftp",
    "map": "messageMapping",
    "message": "contentModifier",
    "processcall": "processCall",
    "processroute": "router",
    "Base64 Decode": "base64Decoder",
    "Base64 Encode": "base64Encoder",
    "Character Decode": "groovyScript",
    "Character Encode": "groovyScript",
    "Combine Documents": "gather",
    "Custom Scripting": "groovyScript",
    "Search/Replace": "messageMapping",
    "Split Documents": "generalSplitter",
    "Mapjsontomultipartformdatamime": "groovyScript",
    "Mapmultipartformdatamimetojson": "groovyScript",
    "Pgp Encrypt": "pgpEncryptor",
    "Pgp Decrypt": "pgpDecryptor",
    "Xslt Ttransformation": "xsltMapping",
    "Zip": "zipCompression",
    "Unzip": "zipDecompression",
    "branch": "sequentialMulticast",
    "route": "router",
    "decision": "router",
    "start": "start",
    "stop": "end",
    "catcherrors": "exceptionSubprocess",
    "exception": "exceptionSubprocess",
    "setproperties": "contentModifier",
    "cache": "data store",
    "flowcontrol": "splitter/multicast/gather",
    "businessrules": "routers/validators",
    "diskconnector": "sftp",
    "customscripting": "groovyScript",
    "documentproperties": "contentModifier",
    "dynamicdocumentproperties": "groovyScript",
    "processproperties": "contentModifier",
    "dynamicprocessproperties": "groovyScript",
    "ftp": "ftp",
    "sftp": "sftp",
    "http": "http",
    "mail": "mail",
    "odata": "odata",
    "rest": "http",
    "salesforce": "salesforce",
    "netsuite": "netsuite",
    "successfactors": "successfactors",
    "successfactorsmaster-Q2Q93V-SFSF-priv_prod": "successfactors",
    "wssoapclientsdk": "soap",
    "cleanse": "NA",
    "programcommand": "groovyScript",
    "aws": "openConnector",
    "findchanges": "messageMapping",
    "dataprocess": "Base64-Encode/Decode/Spiltter/zip-unzip/encrypt-decrypt/xslt",
    "returndocuments": "end",
    "notify": "groovy script with mpl logs"
}


def get_xml_from_boomi(process_id, username, password, accound_id):
    url = f"https://api.boomi.com/api/rest/v1/{accound_id}/Component/{process_id}/export"
    headers = {
        "Accept": "application/xml"
    }
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), headers=headers)
        if response.status_code == 200:
            # print(response.text) # for printing xml response
            return response.text
        print("Failed export:", response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        print("Export error:", e)
    return None


def convert_xml_to_json(xml_data):
    return json.loads(json.dumps(xmltodict.parse(xml_data)))


def build_csv_from_json(json_data):
    output = io.StringIO()
    step_no = 0

    fieldnames = ["StepNo", "ShapeLabel", "OriginalType", "CPIAlternative"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    components = json_data.get("bns:Component", {})
    if isinstance(components, dict):
        components = [components]

    for component in components:
        name = component.get("@name", "")
        shape_label = name

        shapes = component.get("bns:object", {}).get("process", {}).get("shapes", {}).get("shape", [])
        if isinstance(shapes, dict):
            shapes = [shapes]

        for shape in shapes:
            shape_name = shape.get("@userlabel", "null")
            step_no += 1
            if shape_name != "":
                shape_label = shape_name 
            
            original_type = shape.get("@shapetype", "")
            cpi_alternative = shapes_mappings.get(original_type, "NA")

            writer.writerow({
                "StepNo"           : step_no,
                "ShapeLabel"       : shape_label,
                "OriginalType"     : original_type,
                "CPIAlternative"   : cpi_alternative
            })
    return output.getvalue()


# It removes single and double quotes from the strings
def clean_configuration(csv_data):
    csv_data = csv_data.replace("\"", "").replace("\'", "")
    return csv_data


def parse_process_xml_to_metadata(xml_data):
    json_data = convert_xml_to_json(xml_data)

    # Generate CSV
    csv_data = build_csv_from_json(json_data)

    cleaned_csv = clean_configuration(csv_data)

    return cleaned_csv


# Get all data and convert it to csv file and return to main program
def get_all_data(username, password, account_id, selected_processes):
    all_csv_parts = []
    for process_id in selected_processes:
        xml_data = get_xml_from_boomi(process_id, username, password, account_id)
        with open("xml_data.xml", "w") as text_file:
            text_file.write(xml_data)
        if xml_data:
            csv_string = parse_process_xml_to_metadata(xml_data)
            csv_lines = csv_string.splitlines()  # Safer than split('\n')
            all_csv_parts.append(csv_lines[1:])  # Skip header

    # Combine all rows under one header
    final_csv = io.StringIO()
    writer = csv.writer(final_csv)
    writer.writerow(["StepNo", "ShapeLabel", "OriginalType", "CPIAlternative", "RevisedSequence", "Status"])
    for part in all_csv_parts:
        for line in part:
            writer.writerow(line.split(','))

    csv_text = final_csv.getvalue()
    return csv_text