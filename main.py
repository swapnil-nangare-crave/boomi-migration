import io
import re
import csv
import zipfile
import requests
from flask import Flask, render_template, send_file, jsonify, request

from evaluate import run_evaluation
from extract import get_all_processes, extract_process_name_id, get_all_data

app = Flask(__name__)

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

# Extract Function
@app.route("/extract", methods=["GET", "POST"])
def extract_process_metadata():
    if request.method == "GET":
        return render_template("extract_form.html")

    acc_id = request.form.get("boomiaccountId")
    username = request.form.get("boomiUsername")
    password = request.form.get("boomiPassword")
    selected_processes = request.form.getlist("selected_processes")

    if not selected_processes:
        raw_response = get_all_processes(username, password, id=acc_id)
        if not raw_response:
            return render_template("extract_form.html", message="Failed to retrieve processes.")

        process_dict = extract_process_name_id(raw_response)
        return render_template("extract_form.html", processes=process_dict)

    
    csv_text = get_all_data(username, password, acc_id, selected_processes)
    try:
        if csv_text:
            table_html = csv_to_html_table(csv_text)
            return render_template("extract_result.html", table=table_html, csv_data=csv_text)
        else:
            return render_template("extract_form.html", message=csv_text.text)

    except requests.RequestException as e:
        return jsonify({'error': f'Connection failed: {str(e)}'}), 502

# Evaluate Function
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


# Migration Function

# import secrets
# app.secret_key = secrets.token_hex(16)
# from migration import migration_bp  # adjust import if needed
# app.register_blueprint(migration_bp)
import migration as migration
@app.route("/migrate", methods=["GET", "POST"])
def migrate_processes():
    if request.method == "GET":
        return render_template("migration.html")

    acc_id = request.form.get("boomiaccountId")
    username = request.form.get("boomiUsername")
    password = request.form.get("boomiPassword")
    selected_processes = request.form.getlist("selected_processes")

    if not selected_processes:
        raw_response = get_all_processes(username, password, acc_id)
        if not raw_response:
            return render_template("migration.html", message="Failed to retrieve processes.")

        process_dict = extract_process_name_id(raw_response)
        return render_template("migration.html", processes=process_dict)


    csv_text = migration.get_all_data(username, password, acc_id, selected_processes)
    try:
        if csv_text:
            table_html = csv_to_html_table(csv_text)
            return render_template("migration.html", table=table_html, csv_data=csv_text)
        else:
            return render_template("migration.html", message=csv_text.text)

    except requests.RequestException as e:
        return jsonify({'error': f'Connection failed: {str(e)}'}), 502


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
