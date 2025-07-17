# from flask import Blueprint, render_template, request, session, redirect, url_for, send_file
import requests
import io
import csv

# migration_bp = Blueprint('migration', __name__)

def get_all_processes(username, password, account_id):
    url = f"https://boomi.example.com/api/{account_id}/processes"
    resp = requests.get(url, auth=(username, password))
    resp.raise_for_status()
    data = resp.json()
    return {str(p['id']): p['name'] for p in data['processes']}

def get_specific_process(username, password, account_id, process_id):
    url = f"https://boomi.example.com/api/{account_id}/processes/{process_id}"
    resp = requests.get(url, auth=(username, password))
    resp.raise_for_status()
    return resp.json()

def get_subprocess_dependencies(username, password, account_id, process_id):
    url = f"https://boomi.example.com/api/{account_id}/processes/{process_id}/dependencies"
    resp = requests.get(url, auth=(username, password))
    resp.raise_for_status()
    return resp.json()

def get_reusable_resources(username, password, account_id, process_id):
    url = f"https://boomi.example.com/api/{account_id}/processes/{process_id}/resources"
    resp = requests.get(url, auth=(username, password))
    resp.raise_for_status()
    return resp.json()

def json_to_csv(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    headers = data[0].keys() if isinstance(data, list) and data else []
    writer.writerow(headers)
    for row in data:
        writer.writerow([row.get(h, '') for h in headers])
    return output.getvalue()

# @migration_bp.route('/migrate', methods=['GET', 'POST'])
# def migrate():
#     if request.method == 'GET':
#         session.clear()
#         return render_template('migration.html')

#     # POST
#     account_id = request.form['boomiaccountId']
#     username = request.form['boomiUsername']
#     password = request.form['boomiPassword']
#     selected = request.form.getlist('selected_processes')

#     session['creds'] = (username, password, account_id)

#     try:
#         procs = get_all_processes(username, password, account_id)
#     except Exception as e:
#         return render_template('migration.html', message=f"Error: {e}")
#     return render_template('migration.html', processes=procs)

    