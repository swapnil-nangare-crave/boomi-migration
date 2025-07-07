import re 

# Evaluate Process
# --- Step 1: Categorize Processes ---
def categorizeProcesses(csv_input):
    migrateShapes = ["message", "processcall", "processroute", "Xslt Transformation", "zip", 
                     "Unzip", "dataprocess", "Base64 Decode", "Base64 Encode", "Pgp Encrypt", 
                     "pgp Decrypt", "Split Documents", "branch", "route", "start", "noaction:", 
                     "stop", "trycatch", "catcherrors", "dataprocess", "returndocuments"]
    adaptShapes = ["setproperties", "map", "cache", "flowcontrol", "Character Decode", 
                   "Character Encode", "Combine Documents", "Search/Replace", "Custom Scripting", 
                   "customscripting", "documentproperties", "dynamicdocumentproperties", 
                   "processproperties", "dynamicprocessproperties", "notify", "decision", "exception"]
    migrateConnectors = ["ftp", "sftp", "http", "mail", "odata", "rest", 
                         "salesforceconnector", "wssoapclientsdk"]
    adaptConnectors = ["disk", "successfactorsmaster-Q2Q93V-SFSF-priv_prod"]
    
    lines = csv_input.split('\n')
    header = lines[0]
    result = ["Category," + header]
    
    for line in lines[1:]:
        if not line.strip():
            continue
        row = line.split(',')
        shapeType = row[3].strip() if len(row) > 3 else ""
        configuration = ','.join(row[4:]) if len(row) > 4 else ""
        category = "Evaluate"
        
        if shapeType in ["connectoraction", "start"]:
            connectorType = extractConnectorType(configuration)
            if connectorType and connectorType in migrateConnectors:
                category = "Migrate"
            elif connectorType and connectorType in adaptConnectors:
                category = "Adapt"
            elif shapeType == "start" and "connectoraction" not in line:
                category = "Migrate"
        elif shapeType == "dataprocess":
            nameMatch = re.search(r'@name:([^,]+)', configuration)
            if nameMatch:
                name = nameMatch.group(1).strip()
                if name in migrateShapes:
                    category = "Migrate"
                elif name in adaptShapes:
                    category = "Adapt"
        elif shapeType in migrateShapes:
            category = "Migrate"
        elif shapeType in adaptShapes:
            category = "Adapt"
        result.append(f"{category},{line}")
    return '\n'.join(result)

def extractConnectorType(configuration):
    connectorTypeMatch = re.search(r'@connectorType\s*:\s*([^,\s]+)', configuration)
    return connectorTypeMatch.group(1) if connectorTypeMatch else None

# Make Main Report
# --- Step 2: Group By Component/Process ---
def evaluateProcesses(csvInput):
    lines = csvInput.split('\n')
    header = lines[0]
    datalines = lines[1:]

    groupedMap = {}

    for line in datalines:
        row = line.split(',')
        category  = row[0].strip()
        componentId = row[1].strip()
        processName = row[2].strip()

        if componentId not in groupedMap:
            groupedMap[componentId] = {
                'componentId': componentId,
                'processName': processName,
                'categories': []
            }
        groupedMap[componentId]['categories'].append(category)

    for key, value in groupedMap.items():
        categories = value['categories']
        if "Evaluate" in categories:
            value['finalCategory'] = "Evaluate"
        elif "Adapt" in categories:
            value['finalCategory'] = "Adapt"
        else:
            value['finalCategory'] = "Migrate"
        # Debug print
        # print(f"Determined final category for {key}: {value['finalCategory']}")

    # Build result CSV
    result_lines = ["ComponentId,ProcessName,Category"]
    for key, value in groupedMap.items():
        result_lines.append(f"{value['componentId']},{value['processName']},{value['finalCategory']}")

    return '\n'.join(result_lines)

# Count Shape Type
# --- Step 3: Count Shape Types ---
def count_shape_type(csv_input):
    """
    Type,Count,Alternative
    start,1,start
    ftp,1,ftp
    map,1,messageMapping
    mail,1,mail
    stop,1,end
    sftp,1,sftp
    decision,1,router
    processcall,2,processCall
    """
    lines = csv_input.split('\n')

    # Initialize a dictionary to count shape types
    shape_type_counts = {}

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

    # Skip the header and process each line
    for line in lines[1:]:
        if not line.strip():
            continue
        row = line.split(',')
        # Check if the row has at least 6 elements (index 4 is shapeType, 5+ is configuration)
        # Assuming your CSV is: ...shapeType,configuration,...
        # Actually, in your Groovy code, row[4] is shapeType, row[5..-1] is configuration
        if len(row) >= 5:
            shape_type = row[3].strip()
            configuration = ','.join(row[4:]) if len(row) > 5 else ""
            
            # Handle `connectoraction` shape type
            if shape_type == "connectoraction":
                connector_type_match = re.search(r'@connectorType:([^,\s]+)', configuration)
                if connector_type_match:
                    shape_type = connector_type_match.group(1).strip()
            
            # Handle `start` shape type
            elif shape_type == "start":
                connector_type_match = re.search(r'@connectorType:([^,\s]+)', configuration)
                if connector_type_match:
                    shape_type = connector_type_match.group(1).strip()
            
            # Increment the count for the shape type
            shape_type_counts[shape_type] = shape_type_counts.get(shape_type, 0) + 1

    # Build the summary CSV
    result = ["Type,Count,Alternative"]
    for shape_type, count in shape_type_counts.items():
        alternative = shapes_mappings.get(shape_type, "NA")
        result.append(f"{shape_type},{count},{alternative}")
    
    return '\n'.join(result)

# Calculate Statistics
# --- Step 4: Calculate Statistics ---
def calculate_statistics(csv_input):
    """
    Category,Count,Percentage
    Adapt,2,100.00%
    Evaluate,0,0.00%
    Migrate,0,0.00%
    """
    # Split into lines, remove empty/whitespace-only lines
    lines = [line.strip() for line in csv_input.split('\n') if line.strip()]
    if not lines:
        return "Category,Count,Percentage\nNo Data,0,0.00%"

    header = lines[0]

    # Skip header
    data_lines = lines[1:]

    # Map to count each category
    category_count_map = {"Adapt":0, "Evaluate":0, "Migrate":0}

    for line in data_lines:
        if not line.strip():
            continue
        row = line.split(',')
        if len(row) > 2:
            category = row[2].strip()
            category_count_map[category] = category_count_map.get(category, 0) + 1       

    # Total number of processes
    total_count = len(data_lines)

    # Build result lines
    result_lines = ["Category,Count,Percentage"]
    for category, count in category_count_map.items():
        percentage = (count / total_count) * 100
        result_lines.append(f"{category},{count},{percentage:.2f}%")

    return '\n'.join(result_lines)


# Make PDFfrom reportlab.lib import colors
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
import csv
from io import StringIO

def ensure_table_data(table_data):
    """Convert input to list of lists (required for ReportLab tables)"""
    if isinstance(table_data, str):
        # If it's a CSV string, use csv.reader to split into rows and columns
        f = StringIO(table_data)
        reader = csv.reader(f)
        return [row for row in reader]
    elif isinstance(table_data, list):
        if len(table_data) > 0 and isinstance(table_data[0], str):
            # If it's a list of strings, split each string into columns
            return [row.split(',') for row in table_data]
        else:
            # Already a list of lists
            return table_data
    else:
        raise ValueError("Unsupported input type for table data")

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
    return [["Total Processes","Main Processes","Sub-Processes"],[total,main,sub]]

def build_pdf(filename, shape_data, category_data, sub_process):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title and info
    elements.append(Paragraph("<b>Move From Boomi to SAP Integration Suite</b>", styles['Title']))
    elements.append(Paragraph("Migration Assessment Report", styles['Heading2']))
    elements.append(Paragraph(f"Date of Report: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Agenda
    elements.append(Paragraph("<b>Contents</b>", styles['Heading3']))
    elements.append(Paragraph("Introduction<br/>Migration Assessment<br/>Assessment Categories<br/>Scenario Categorization Summary<br/>Adapter Type Summary", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Introduction and Assessment
    elements.append(Paragraph("<b>Introduction</b>", styles['Heading2']))
    elements.append(Paragraph("By introducing the SAP Business Technology Platform (BTP), the integration topic has moved to a new stage. Certainly, there is an infrastructure change running cloud-based services and solutions. This means that administration and operational tasks may differ. The innovative technology also impacts the SAP Integration Suite design and runtime. Nested as a service on SAP BTP, SAP Integration Suite runs in SAP BTP, Cloud Foundry environment. This foundation is an open-source platform as a service (PaaS). It is designed to be configured, deployed, managed, scaled, and upgraded on any cloud Infrastructure as a Service (IaaS) provider. Please be aware of what features the Cloud Foundry environment on SAP BTP supports and doesn't support. However, the intention of SAP Integration Suite is to connect and automate processes and data efficiently across the heterogeneous IT landscape and business network by providing comprehensive integration capabilities and best practices to accelerate and modernize integration.", styles['Normal']))
    elements.append(Paragraph("<b>Migration Assessment</b>", styles['Heading2']))
    elements.append(Paragraph("<b>Assessment Categories</b>", styles['Heading3']))
    elements.append(Paragraph("<font color='green'><b>• Ready to migrate:</b></font> These Boomi processes match to the SAP Integration Suite. They can be moved manually to the SAP Integration Suite. The move might include additional steps within SAP Integration Suite to configure this scenario properly.", styles['Normal']))
    elements.append(Paragraph("<font color='blue'><b>• Adjustment required:</b></font> These Boomi processes partially match to the scenarios offered in SAP Integration Suite. They can be moved to SAP Integration Suite manually. Further adjustments to the end-to-end integration process based on best practices are required.", styles['Normal']))
    elements.append(Paragraph("<font color='red'><b>• Evaluation required:</b></font> For these Boomi processes, some items require further evaluation before the scenario can be moved to SAP Integration Suite.", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Scenario Categorization Summary Table
    elements.append(Paragraph("<b>Scenario Categorization Summary:</b>", styles['Heading2']))
    category_table_data = ensure_table_data(category_data)
    
    # Creating custom order and adding sub_proces in data
    desired_order = ['Migrate', 'Adapt', 'Evaluate']
    header = category_table_data[0]
    data_rows = category_table_data[1:]
    data_rows_sorted = sorted(
        data_rows,
        key=lambda row: desired_order.index(row[0])
    )
    category_table_data = [header] + data_rows_sorted

    category_table_data.extend(sub_process)


    t = Table(category_table_data, colWidths=[120, 120, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Summary paragraph (dynamic, based on data)
    migrate = category_table_data[1][2]
    adapt = category_table_data[2][2]
    evaluate = category_table_data[3][2]
    
    summary = (
        f"<b>Based on our migration assessment:</b><br/>"
        f"• {migrate} of the Boomi processes reviewed from your current Boomi Account can be moved manually to the SAP Integration Suite.<br/>"
        f"• {adapt} of the Boomi processes reviewed from your current Boomi Account can be moved manually with some adjustments.<br/>"
        f"• {evaluate} of the interfaces should be further analyzed and re-evaluated prior to the move to SAP Integration Suite."
    )
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Adapter Type Summary Table
    elements.append(Paragraph("<b>Adapter/Connector/Shape Type Summary:</b>", styles['Heading2']))
    shape_table_data = ensure_table_data(shape_data)
    t2 = Table(shape_table_data, colWidths=[200, 60, 200])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("<font color='orange'><b>Thank you!</b></font>", styles['Heading2']))

    doc.build(elements)

# --- MAIN WORKFLOW ---
def run_evaluation(csv_input):
    # Step 2: Categorize processes
    fullEvaluation = categorizeProcesses(csv_input)
    with open("fullEvaluation.csv", mode='w', encoding='utf-8', newline='') as f:
        f.write(fullEvaluation)

    # Step 3: Group by process
    mainResult = evaluateProcesses(fullEvaluation)
    with open("mainResult.csv", mode='w', encoding='utf-8') as f:
        f.write(mainResult)

    # Step 4: Count shapes
    shape_data = count_shape_type(csv_input)

    # Step 5: Calculate statistics
    category_data = calculate_statistics(mainResult)

    # Step 6: Calculate subprocess summary
    sub_process = calculate_subprocess_summary(csv_input)

    # Step 7: Generate PDF report
    pdf_filename = "Migration_Assessment_Report.pdf"
    build_pdf(pdf_filename, shape_data, category_data, sub_process)

    return "fullEvaluation.csv", "mainResult.csv", pdf_filename


"""
- need to handle the lines between the fullEvaluation  
- finding single alternatives for dataprocess in pdf 
"""