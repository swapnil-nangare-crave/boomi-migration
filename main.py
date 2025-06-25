import io
import os
import re
import csv
import zipfile
import requests
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, render_template, send_file, jsonify
from evaluate import run_evaluation

# Load env variables
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

app = Flask(__name__)

# CPI URLs
IFLOW_URL = os.getenv('IFLOW_URL')
CPI_IFLOW_URL = f"{IFLOW_URL}extractprocessmetadata"
PDF_GENERATE_URL = f"{IFLOW_URL}makeresultpdf"

COMMON_HEADERS = {
    'Accept': 'text/plain',
    'Content-Type': 'text/plain',
    'X-Requested-With': 'XMLHttpRequest'
}

TIMEOUT = 60

_pdf_cache = None
_main_csv_cache = None
_full_csv_cache = None

# -------------------------------------
# Utilities
# -------------------------------------

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
    header_html = "".join(f"<th>{html.escape(col)}</th>" for col in rows[0])
    header_html += "".join("<th></th>" for _ in range(max_columns - len(rows[0])))

    html_table = f'''
    <table class="table table-sm table-striped table-bordered align-middle shadow-sm rounded">
        <thead class="table-light">
            <tr>{header_html}</tr>
        </thead>
        <tbody>
    '''

    for row in rows[1:]:
        padded_row = row + [""] * (max_columns - len(row))
        row_html = "".join(
            f"<td>{html.escape(cell) if cell.strip() else '<span class=\"text-muted\">—</span>'}</td>"
            for cell in padded_row
        )
        html_table += f"<tr>{row_html}</tr>"

    html_table += "</tbody></table>"
    return html_table


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


# -------------------------------------
# Routes
# -------------------------------------

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/help", methods=["GET"])
def help():
    return render_template("help.html")


from flask import Flask, request, render_template
from extract import (
    csv_to_html_table,
    get_all_processes,
    extract_process_name_id,
    export_process_and_return_xml,
    parse_process_xml_to_metadata
)

@app.route("/extract", methods=["GET", "POST"])
def extract_process_metadata():
    if request.method == "GET":
        return render_template("extract_form.html")

    acc_id = request.form.get("boomiaccountId")
    username = request.form.get("boomiUsername")
    password = request.form.get("boomiPassword")
    selected_processes = request.form.getlist("selected_processes")

    if not selected_processes:
        # First POST: show process list in modal
        raw_response = get_all_processes(username, password, id=acc_id)
        if not raw_response:
            return render_template("extract_form.html", message="Failed to retrieve processes.")

        process_dict = extract_process_name_id(raw_response)
        return render_template("extract_form.html", processes=process_dict)

    print("-"*40)
    # 2nd POST: Process(es) selected, do export and parse
    # Generate CSV content from all selected processes
    all_csv_parts = []
    for pid in selected_processes:
        xml_data = export_process_and_return_xml(pid, username, password, acc_id)
        if xml_data:
            csv_string = parse_process_xml_to_metadata(xml_data)
            csv_lines = csv_string.splitlines()  # Safer than split('\n')
            all_csv_parts.append(csv_lines[1:])  # Skip only the first line (header) # Skip header

    # Combine all rows under one header
    final_csv = io.StringIO()
    writer = csv.writer(final_csv)
    writer.writerow(["ComponentId", "ProcessName", "ShapeName", "ShapeType", "Configuration"])
    for part in all_csv_parts:
        for line in part:
            writer.writerow(line.split(','))

    csv_text = final_csv.getvalue()
    try:
        if csv_text:
            table_html = csv_to_html_table(csv_text)
            return render_template("extract_result.html", table=table_html, csv_data=csv_text)
        else:
            return render_template("extract_form.html", message=csv_text.text)

    except requests.RequestException as e:
        return jsonify({'error': f'Connection failed: {str(e)}'}), 502



# @app.route("/extract", methods=["GET", "POST"])
# def extract_process_metadata():
#     if request.method == "GET":
#         return render_template("extract_form.html")

#     boomiaccountId = request.form.get('boomiaccountId')
#     boomiUsername = request.form.get('boomiUsername')

#     if not boomiaccountId or not boomiUsername:
#         return jsonify({'error': 'Missing Boomi Account ID or Username'}), 400

#     try:
#         response = requests.get(
#             CPI_IFLOW_URL,
#             params={'boomiaccountId': boomiaccountId, 'boomiUsername': boomiUsername},
#             headers=COMMON_HEADERS,
#             timeout=TIMEOUT
#         )

#         if response.ok:
#             csv_text = response.content.decode('utf-8', errors='replace')
#             table_html = csv_to_html_table(csv_text)
#             return render_template("extract_result.html", table=table_html, csv_data=csv_text)
#         else:
#             return render_template("extract_form.html", message=response.text)

#     except requests.RequestException as e:
#         return jsonify({'error': f'Connection failed: {str(e)}'}), 502


@app.route("/evaluate", methods=["GET", "POST"])
def evaluate_process_metadata():
    global _pdf_cache, _main_csv_cache, _full_csv_cache

    if request.method == "GET":
        return render_template("evaluate_form.html")

    uploaded_file = request.files.get("csvfile")
    csv_data = uploaded_file.read().decode("utf-8") if uploaded_file else request.form.get("csv_data")

    if not csv_data:
        return render_template("evaluate_form.html", message="Please upload or paste a CSV file.")

    try:
        # Run full evaluation locally
        full_eval_file, main_result_file, pdf_file = run_evaluation(csv_data)

        # Read contents back for rendering and caching
        with open(full_eval_file, 'r', encoding='utf-8') as f:
            full_eval_csv = f.read()

        with open(main_result_file, 'r', encoding='utf-8') as f:
            main_result_csv = f.read()

        with open(pdf_file, 'rb') as f:
            _pdf_cache = f.read()

        _main_csv_cache = main_result_csv
        _full_csv_cache = full_eval_csv
    
        return render_template(
            "evaluate_result.html",
            main_result=csv_to_html_table(main_result_csv),
            full_evaluation=csv_to_html_table(full_eval_csv),
            main_result_csv=main_result_csv,
            full_eval_csv=full_eval_csv,
            pdf_url="/download/pdf",
            main_csv_url="/download/main",
            full_csv_url="/download/full"
        )

    except Exception as e:
        return render_template("evaluate_form.html", message=f"Evaluation failed: {str(e)}")


@app.route("/download/main")
def download_main_csv():
    if _main_csv_cache:
        return send_file(
            io.BytesIO(_main_csv_cache.encode('utf-8')),
            mimetype="text/csv",
            as_attachment=True,
            download_name="mainResult.csv"
        )
    return "Main CSV not available", 404

@app.route("/download/full")
def download_full_csv():
    if _full_csv_cache:
        return send_file(
            io.BytesIO(_full_csv_cache.encode('utf-8')),
            mimetype="text/csv",
            as_attachment=True,
            download_name="fullEvaluation.csv"
        )
    return "Full Evaluation CSV not available", 404

@app.route("/download/pdf")
def download_pdf():
    return send_file(
        io.BytesIO(_pdf_cache),
        mimetype='application/pdf',
        as_attachment=False,
        download_name='Result.pdf'
    )


@app.route("/download_zip", methods=["POST"])
def download_zip():
    main_csv = request.form.get("main_csv")
    full_csv = request.form.get("full_csv")
    if not main_csv or not full_csv:
        return "Missing CSV data", 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        zipf.writestr("MainResult.csv", main_csv)
        zipf.writestr("FullEvaluationResult.csv", full_csv)
        zipf.writestr("Result.pdf", _pdf_cache)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="evaluation_bundle.zip"
    )


@app.route("/download_csv", methods=["POST"])
def download_csv():
    csv_data = request.form.get("csv_data")
    if not csv_data:
        return "No CSV data provided", 400

    return send_file(
        io.BytesIO(csv_data.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="response_data.csv"
    )


# -------------------------------------
# Run the app
# -------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
