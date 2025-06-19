import io
from flask import Flask, request, jsonify, send_file, render_template
import requests
import csv
import os
from dotenv import load_dotenv
from pathlib import Path
import zipfile
import tempfile
import re
# Load the .env
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

app = Flask(__name__)


# Constants
IFLOW_URL = os.getenv('IFLOW_URL')
CPI_IFLOW_URL = f"{IFLOW_URL}extractprocessmetadata" 
CPI_EVALUATE_URL = f"{IFLOW_URL}evaluateprocessmetadata"
PDF_GENERATE_URL = f"{IFLOW_URL}makeresultpdf"         

print("Loaded CPI_IFLOW_URL:", CPI_IFLOW_URL)

COMMON_HEADERS = {
    'Accept': 'text/plain',
    'Content-Type': 'text/plain',
    'X-Requested-With': 'XMLHttpRequest'
}

TIMEOUT = 60


# Utilities
def handle_cpi_response(response: requests.Response = None, is_download=False, csv_data: str = None):
    if is_download:
        # Use response.content if response is given, otherwise use csv_data
        content = response.content if response else csv_data.encode('utf-8')
        return send_file(
            io.BytesIO(content),
            mimetype='text/csv',
            as_attachment=True,
            download_name='response_data.csv'
        )

    # Regular decoding if response is passed
    if response:
        return response.content.decode('utf-8', errors='replace')
    
    return None

def csv_to_html_table(csv_text):
    import html

    try:
        dialect = csv.Sniffer().sniff(csv_text.splitlines()[0])
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(csv_text.splitlines(), dialect)
    rows = list(reader)

    if not rows:
        return "<p>No data available</p>"

    max_columns = max(len(row) for row in rows)

    html_table = '''
    <table class="table table-sm table-striped table-bordered align-middle shadow-sm rounded">
        <thead class="table-light">
            <tr>{}</tr>
        </thead>
        <tbody>
    '''.format("".join(f"<th>{html.escape(col)}</th>" for col in rows[0]) + "".join("<th></th>" for _ in range(max_columns - len(rows[0]))))

    for row in rows[1:]:
        padded_row = row + [""] * (max_columns - len(row))  # Ensure same length
        html_table += "<tr>" + "".join(
            f"<td>{html.escape(cell) if cell.strip() else '<span class=\'text-muted\'>—</span>'}</td>" for cell in padded_row
        ) + "</tr>"

    html_table += "</tbody></table>"
    return html_table




@app.route("/", methods=["GET"])
def home():
    return render_template("base.html")

@app.route("/download_csv", methods=["POST"])
def download_csv():
    csv_data = request.form.get("csv_data")
    if not csv_data:
        return "No CSV data provided", 400

    return handle_cpi_response(is_download=True, csv_data=csv_data)

@app.route("/extract", methods=["GET", "POST"])
def extract_process_metadata():
    if request.method == "GET":
        return render_template("extract_form.html")

    boomiaccountId = request.form.get('boomiaccountId')
    boomiUsername = request.form.get('boomiUsername')

    if not boomiaccountId or not boomiUsername:
        return jsonify({'error': 'Missing Boomi Account ID or Username'}), 400

    try:
        response = requests.get(
            CPI_IFLOW_URL,
            params={'boomiaccountId': boomiaccountId, 'boomiUsername': boomiUsername},
            headers=COMMON_HEADERS,
            timeout=TIMEOUT
        )
        if response.ok:
            csv_text = response.content.decode('utf-8', errors='replace')
            table_html = csv_to_html_table(csv_text)
            return render_template("extract_result.html", table=table_html, csv_data=csv_text)
        else:
            message = response.content.decode('utf-8', errors='replace')
            return render_template('extract_form.html', message=message)
            
    except requests.RequestException as e:
        return jsonify({'error': f'Failed to connect to CPI iFlow: {str(e)}'}), 502


@app.route("/extract_form", methods=["GET"])
def extract_form():
    return render_template("extract_form.html")


@app.route("/evaluate", methods=["GET", "POST"])
def evaluate_process_metadata():
    if request.method == "GET":
        return render_template("evaluate_form.html")

    # Step 1: Get CSV from upload or hidden input
    uploaded_file = request.files.get("csvfile")
    if uploaded_file and uploaded_file.filename:
        csv_data = uploaded_file.read().decode("utf-8", errors="replace")
    else:
        csv_data = request.form.get("csv_data")
        if not csv_data:
            return render_template("evaluate_form.html", message="Please upload a CSV file or extract one first.")

    # Step 2: Calculate SubProcess summary
    def calculate_subprocess_summary(csv_text):
        lines = csv_text.strip().split("\n")
        component_ids = set()
        subprocess_ids = set()

        for line in lines:
            columns = line.split(",")
            if columns:
                component_ids.add(columns[0].strip())

            if "processcall" in line:
                match = re.search(r"@processId:([^\s,]+)", line)
                if match:
                    subprocess_ids.add(match.group(1).strip())

        total = len(component_ids) - 1
        sub = len(subprocess_ids)
        main = total - sub
        return f"Total Processes,Main Processes,Sub-Processes\n{total},{main},{sub}"

    subprocess_summary = calculate_subprocess_summary(csv_data)

    # Step 3: Call CPI Evaluate Endpoint
    try:
        eval_response = requests.post(
            CPI_EVALUATE_URL,  # built from IFLOW_URL + "evaluateprocessmetadata"
            data=csv_data,
            headers=COMMON_HEADERS,
            timeout=TIMEOUT
        )

        if not eval_response.ok:
            return render_template("evaluate_form.html", message="CPI Evaluate call failed.")

        parts = re.split(r"\n\s*\n", eval_response.text.strip())
        if len(parts) < 4:
            return render_template("evaluate_form.html", message="Unexpected response format from CPI Evaluate.")

        shape_summary = parts[0].strip()
        category_summary = parts[1].strip()
        main_result_csv = parts[2].strip()
        full_eval_csv = parts[3].strip()

        # Step 4: Call CPI PDF generator using PDF_GENERATE_URL from .env
        combined_pdf_input = f"{shape_summary}\n{category_summary}\n{subprocess_summary}"
        pdf_response = requests.post(
            PDF_GENERATE_URL,  # built from IFLOW_URL + "makeresultpdf"
            data=combined_pdf_input,
            headers={
                'Accept': 'application/pdf',
                'Content-Type': 'text/plain',
                'X-Requested-With': 'XMLHttpRequest',
            },
            timeout=TIMEOUT
        )

        if not pdf_response.ok:
            return render_template("evaluate_form.html", message="PDF generation failed.")

        # Step 5: Create a ZIP file with all 3 outputs
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            zipf.writestr("MainResult.csv", main_result_csv)
            zipf.writestr("FullEvaluationResult.csv", full_eval_csv)
            zipf.writestr("Result.pdf", pdf_response.content)

        return send_file(
            temp_zip.name,
            mimetype="application/zip",
            as_attachment=True,
            download_name="evaluation_bundle.zip"
        )

    except requests.RequestException as e:
        return render_template("evaluate_form.html", message=f"Failed to connect to CPI: {str(e)}")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
