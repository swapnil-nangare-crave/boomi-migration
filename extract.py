# extract.py
import requests
from requests.auth import HTTPBasicAuth
import csv
import io
import json
import xmltodict

def get_all_processes(username, password, id):
    url = f"https://api.boomi.com/api/rest/v1/{id}/Process/query"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, auth=HTTPBasicAuth(username, password), headers=headers)
        if response.status_code == 200:
            return response.json()
        print("Error:", response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        print("Request Exception:", e)
    return None


def extract_process_name_id(json_data):
    process_map = {}
    for item in json_data.get("result", []):
        name = item.get("name")
        process_id = item.get("id")
        if name and process_id:
            process_map[name] = process_id
    return process_map


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


def convert_xml_to_json(xml_data):
    return json.loads(json.dumps(xmltodict.parse(xml_data)))


def build_csv_from_json(json_data):
    output = io.StringIO()

    fieldnames = ["ComponentId", "ProcessName", "ShapeName", "ShapeType", "Configuration"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    components = json_data.get("bns:Component", {})
    if isinstance(components, dict):
        components = [components]

    for component in components:
        component_id = component.get("@componentId", "")
        name = component.get("@name", "")

        shapes = component.get("bns:object", {}).get("process", {}).get("shapes", {}).get("shape", [])
        if isinstance(shapes, dict):
            shapes = [shapes]

        for shape in shapes:
            shape_name = shape.get("@userlabel", "null")
            shape_type = shape.get("@shapetype", "")
            config = shape.get("configuration", {})

            config_str = ";".join(f"{k}:{v}" for k, v in config.items())

            writer.writerow({
                "ComponentId": component_id,
                "ProcessName": name,
                "ShapeName": shape_name,
                "ShapeType": shape_type,
                "Configuration": config_str
            })
    return output.getvalue()

# Get all data and convert it to csv file and return to main program
def get_all_data(username, password, accound_id, selected_processes):
    all_csv_parts = []
    for process_id in selected_processes:
        xml_data = get_xml_from_boomi(process_id, username, password, accound_id)
        if xml_data:
            csv_string = parse_process_xml_to_metadata(xml_data)
            csv_lines = csv_string.splitlines()  # Safer than split('\n')
            all_csv_parts.append(csv_lines[1:])  # Skip header

    # Combine all rows under one header
    final_csv = io.StringIO()
    writer = csv.writer(final_csv)
    writer.writerow(["ComponentId", "ProcessName", "ShapeName", "ShapeType", "Configuration"])
    for part in all_csv_parts:
        for line in part:
            writer.writerow(line.split(','))

    csv_text = final_csv.getvalue()
    return csv_text