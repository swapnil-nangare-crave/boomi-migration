# extract.py
import requests
from requests.auth import HTTPBasicAuth
import csv
import io
import json
import xmltodict


# Render CSV data into HTML table for frontend
def csv_to_html_table(csv_data):
    lines = csv_data.strip().splitlines()
    if not lines:
        return "<p>No data</p>"

    headers = lines[0].split(",")
    html = "<table class='table table-bordered'><thead><tr>"
    html += "".join([f"<th>{h}</th>" for h in headers]) + "</tr></thead><tbody>"

    for row in lines[1:]:
        cells = row.split(",")
        html += "<tr>" + "".join([f"<td>{c}</td>" for c in cells]) + "</tr>"

    html += "</tbody></table>"
    return html


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


def export_process_and_return_xml(process_id, username, password, acc_id):
    url = f"https://api.boomi.com/api/rest/v1/{acc_id}/Component/{process_id}/export"
    headers = {
        "Accept": "application/xml"
    }
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), headers=headers)
        if response.status_code == 200:
            return response.text
        print("Failed export:", response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        print("Export error:", e)
    return None


def parse_process_xml_to_metadata(xml_data):
    json_data = convert_xml_to_json(xml_data)

    # Generate CSV
    csv_data = build_csv_from_json(json_data)

    return csv_data


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
