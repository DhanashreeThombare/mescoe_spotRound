import io
import shutil
from flask import Flask, flash, render_template, request, redirect, send_file, url_for, send_from_directory, make_response
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import tabula
from datetime import datetime, timedelta
import os
import csv
import zipfile
import tabula
import PyPDF2
import pandas as pd
from io import BytesIO
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
import random
app = Flask(__name__)

# Configurations for Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'wadia.admission@mescoepune.org'
app.config['MAIL_PASSWORD'] = 'epwc swxr adti okju'
app.config['MAIL_DEFAULT_SENDER'] = 'wadia.admission@mescoepune.org'

mail = Mail(app)

@app.route('/results', methods=['POST'])
def results():
    # Dummy results for demonstration purposes
    results_dict = {
        'cross_checked': True,
        'jee': [{'key1': 'value1', 'key2': 'value2'}],
        'cet': [{'Unnamed: 0': 'App ID', 'Unnamed: 1': 'Full Name', 'Unnamed: 2': 'Merit Exam'}]
    }
    return render_template('result.html', results_dict=results_dict, cross_checked=True)

# Set the upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set to keep track of uploaded file names
uploaded_files = set()

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

def get_total_pages(pdf_path):
    # Use PyPDF2 to get the total number of pages in the PDF
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        return len(reader.pages)

def pdf_to_csv(pdf_path, output_csv, batch_size=50):
    # Get the total number of pages in the PDF
    total_pages = get_total_pages(pdf_path)

    # Initialize an empty list to store DataFrames
    all_dfs = []

    # Set the initial page number
    page_num = 1

    while page_num <= total_pages:
        # Calculate the end page for the current batch, ensuring it doesn't exceed the total number of pages
        end_page = min(page_num + batch_size - 1, total_pages)

        # Read the PDF file in the current batch of pages
        dfs = tabula.read_pdf(pdf_path, pages=f"{page_num}-{end_page}", multiple_tables=True, lattice=True)

        # If tables were found, add them to the list of DataFrames
        if dfs:
            all_dfs.extend(dfs)

        # Increment the page number for the next batch
        page_num += batch_size

    # Concatenate all DataFrames in the list
    all_tables = pd.concat(all_dfs, ignore_index=True)

    # Write concatenated DataFrame to CSV
    all_tables.to_csv(output_csv, index=False)

with open("pass.txt", 'r') as f:
  correct_password = f.read().strip()

# Add this function to your Python code
def message_level(message):
    # Define logic to determine message level (e.g., success, error, warning, etc.)
    # You can implement this based on your application's requirements
    # For example, if message starts with 'Error', return 'error', otherwise return 'info'
    if message.startswith('Error'):
        return 'error'
    else:
        return 'info'

# Set a unique secret key (replace with your own)
app.secret_key = 'your_unique_and_secret_key_here'

# Function to get available merit lists
def get_available_merit_lists():
    return [file for file in os.listdir(app.config['UPLOAD_FOLDER']) if file.endswith('.csv')]

@app.route('/')
def user():
    return render_template('user.html')

@app.route('/route')
def index():
    return render_template('index.html')

@app.route('/merit_lists', methods=['GET', 'POST'])
def merit_lists():
    if request.method == 'POST':
        selected_merit_list = request.form['merit_list']
        return view_csv(selected_merit_list)
    else:
        available_merit_lists = get_available_merit_lists()
        return render_template('test.html', merit_lists=available_merit_lists)  
    

@app.route('/up')
def up():
    return render_template('upload.html')

# Incremental counter for folder names
folder_counter = 0

@app.route('/finish_round', methods=['POST'])
def finish_round():
    global folder_counter

    # Find a new folder name that doesn't exist
    new_folder_name = f'ROUND_{folder_counter}'
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], new_folder_name)):
        folder_counter += 1
        new_folder_name = f'ROUND_{folder_counter}'

    # Create a new folder for the round
    new_folder_path = os.path.join(app.config['UPLOAD_FOLDER'], new_folder_name)
    os.makedirs(new_folder_path)

    # Move only files from the uploads folder to the new round folder
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        src = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(src):
            dst = os.path.join(new_folder_path, filename)
            shutil.move(src, dst)

    return redirect(url_for('up'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        entered_password = request.form['password']
        if entered_password == correct_password:
            # Valid password, redirect to upload page
            return redirect(url_for('up'))
        else:
            # Invalid password, flash error message
            flash('Invalid password. Please try again.', 'error')  # Add 'error' as second argument
            return redirect(url_for('admin_login'))  # Redirect back to the login page
    return render_template('login.html', message_level=message_level)

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file1' not in request.files or 'file2' not in request.files:
            flash('Please select two files')
            return render_template('upload.html')

        files = [request.files['file1'], request.files['file2']]
        uploaded_and_converted = True

        for idx, file in enumerate(files):
            # If user does not select file, browser also
            # submits an empty part without filename
            if file.filename == '':
                flash(f'No selected file for file {idx+1}')
                uploaded_and_converted = False
                break

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename in uploaded_files:
                    flash(f'File {filename} has already been uploaded and converted')
                    uploaded_and_converted = False
                else:
                    uploaded_files.add(filename)  # Add filename to the set of uploaded files
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)

                    # Convert uploaded PDF to CSV
                    output = os.path.join(app.config['UPLOAD_FOLDER'], f'output{idx+1}.csv')
                    pdf_to_csv(file_path, output)

        if uploaded_and_converted:
            flash('Files uploaded and converted successfully!')
        return render_template('upload.html')
    return render_template('upload.html')




@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def send_email(to_email, otp):
    from_email = "wadia.admission@mescoepune.org"
    from_password = "epwc swxr adti okju"  # Use the app password here

    subject = "OTP for MESWCOE Spot Round Registration"
    body = f"Your OTP code for MESWCOE Spot Round Registration : {otp}."

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = request.json.get('email')
    otp = random.randint(100000, 999999)
    session['otp'] = otp
    session['email'] = email
    if send_email(email, otp):
        return jsonify({'message': 'OTP sent successfully', 'success': True})
    else:
        return jsonify({'message': 'Failed to send OTP'}), 500

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.json.get('otp')
    if 'otp' in session and session['otp'] == int(user_otp):
        session['email_verified'] = True
        return jsonify({'message': 'OTP verified successfully','success': True})
    else:
        session['email_verified'] = False
        return jsonify({'message': 'Invalid OTP'}), 400

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

@app.route('/search', methods=['GET', 'POST'])
def search():
    jee = "JEE"
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        first_name = request.form.get('first_name', '').upper().strip()
        middle_name = request.form.get('middle_name', '').upper().strip()
        last_name = request.form.get('last_name', '').upper().strip()
        mobile = request.form.get('mobile', '').strip()
        mobile1 = request.form.get('mobile1', '').strip()
        address = request.form.get('address', '').strip()
        email = request.form.get('email', '').strip()
        department = request.form.get('departments', '').strip()
        
        file = request.files.get('file')

        # Debugging: Print received form data
        print(f"Received data: query={query}, first_name={first_name}, middle_name={middle_name}, last_name={last_name}, mobile={mobile}, email={email}, department={department}, address={address}")

        if not email or not mobile:
            flash('Please fill in all required fields (email, mobile number).')
            return render_template('search.html')

        # Store email in session after verification
        session['email'] = email
        session['email_verified'] = True
        session['query'] = query

        if not file or file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if not session.get('email_verified'):
            flash('Please verify your email before submitting the form.')
            return redirect(url_for('index'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            base_filename = filename.rsplit('.', 1)[0]
            print(f"Uploaded file: {filename}, Base filename: {base_filename}, Query: {query}")  # Debugging

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            flash('Invalid file type.', 'error')
            return redirect(request.url)

# Extract the PDF file name (without path)
        pdf_file_name = filename

        full_name = f"{first_name} {middle_name} {last_name}".strip()
        first_middle_name = f"{first_name} {middle_name}".strip()
        check_value = f"{first_name} {middle_name} {last_name}"

        results1 = search_data(query, 'output1.csv') 
        results2 = search_data(query, 'output2.csv') 

        check_found = bool(results1 or results2)

        contact_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contact.csv')
        if os.path.exists(contact_csv_path):
            with open(contact_csv_path, 'r', newline='') as contact_file:
                reader = csv.reader(contact_file)
                for row in reader:
                    if query == row[0]:
                        flash('Already applied')
                        return render_template('search.html')

        jee_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'jee.csv')
        with open(jee_csv_path, 'a', newline='') as jee_file:
            writer = csv.writer(jee_file)
            if not results1 and not os.path.getsize(jee_csv_path):
                writer.writerow(results1[0].keys()) if results1 else None
            for row in results1:
                if any(jee == value for value in row.values()):
                    if any(check_value == value for value in row.values()):
                        writer.writerow(row.values())
                        check_found = True
                        break

        cet_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cet.csv')
        with open(cet_csv_path, 'a', newline='') as cet_file:
            writer = csv.writer(cet_file)
            if not results2 and not os.path.getsize(cet_csv_path):
                writer.writerow(results2[0].keys()) if results2 else None
            for row in results2:
                if any(check_value == value for value in row.values()):
                    writer.writerow(row.values())
                    check_found = True
                    break

        if not check_found:
            return render_template('search.html', data_not_found=True)

        if check_found:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            contact_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contact.csv')
            comment = request.form.get('comment', '').strip()
            if not os.path.exists(contact_csv_path):
                with open(contact_csv_path, 'w', newline='') as contact_file:
                    writer = csv.writer(contact_file)
                    writer.writerow(['Application ID', 'Name', 'Department', 'Email', 'Mobile Number', 'Alternate Number', 'Address', 'PDF File Name', 'Timestamp'])

            with open(contact_csv_path, 'a', newline='') as contact_file:
                writer = csv.writer(contact_file)
                writer.writerow([query, check_value, department, email, mobile, mobile1, address, pdf_file_name, timestamp])

                if check_found:
                    for row in results2:
                        value_filename = row.get('Category', '').replace('/', '_')
                        value_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{value_filename}.csv")

                        # Ensure the directory exists
                        ensure_directory_exists(value_csv_path)

                        with open(value_csv_path, 'a', newline='') as value_file:
                            writer = csv.writer(value_file)
                            if not os.path.getsize(value_csv_path):
                                writer.writerow(row.keys())
                            writer.writerow(row.values())

                        sort_csv_file(value_csv_path)
            if results1:
                sort_csv_file(jee_csv_path)
            if results2:
                sort_csv_file(cet_csv_path)

            cross_checked = check_found
            
            return render_template('result.html', results_dict={'jee': results1, 'cet': results2}, cross_checked=cross_checked)
    return render_template('search.html', data_not_found=False)

# Function to search for data in the CSV file based on a specific attribute
def search_data(query, file_name):
    results = []
    with open(os.path.join(app.config['UPLOAD_FOLDER'], file_name), 'r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Loop through all attributes and search for the query
            for attribute, value in row.items():
                if query.lower() in value.lower():
                    results.append(row)
                    break  # Break out of the inner loop if a match is found
    return results


def sort_csv_file(file_path):
    with open(file_path, 'r', newline='') as file:
        all_data = list(csv.reader(file))

    # Filter out rows with non-numeric values in the first column
    def parse_row(row):
        try:
            # Try converting the first column to a float
            row[0] = float(row[0])
        except (ValueError, IndexError):
            # Handle rows where the first column is non-numeric or missing
            row[0] = float('inf')  # Use a placeholder for sorting (e.g., float('inf'))
        return row

    parsed_data = [parse_row(row) for row in all_data]

    # Sort the rows based on the first column
    sorted_data = sorted(parsed_data, key=lambda row: row[0])

    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(sorted_data)


@app.route('/view_csv/<filename>')
def showCSVContent(filename):
    """
    This route retrieves the content of a specified CSV file and returns it as a string.
    """
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash(f"CSV file '{filename}' not found.")
        return redirect(url_for('index'))

    try:
        with open(file_path, 'r', newline='') as file:
            csv_content = file.read()
    except OSError:
        flash(f"Error reading CSV file '{filename}'.")
        return redirect(url_for('index'))

    return csv_content

# Function to add serial number to CSV data
def add_serial_number(csv_content, filename):
    if filename == 'jee.csv':
        column_names = [
            'Serial No',
            'Merit No',
            'Application ID',
            "Candidate's Full Name",
            'Merit Exam',
            'Percentile / Mark',
            'JEE Math Percentile',
            'JEE Physics Percentile',
            'JEE Chemistry Percentile',
            'MHT-CET PCM Total Percentile',
            'MHT-CET Math Percentile',
            'MHT-CET Physics Percentile',
            'MHT-CET Chemistry Percentile',
            'HSC PCM %',
            'HSC Math %',
            'HSC Physics %',
            'HSC / Diploma / D. Voc. Total %',
            'SSC Total %',
            'SSC Math %',
            'SSC Science %',
            'SSC English %'
        ]
    elif filename == 'contact.csv':
        # For contact.csv, return the content as is without adding serial numbers
        return csv_content
    else:
        # Default column names
        column_names = [
            'Serial No',
            'Merit No',
            'Application ID',
            "Candidate's Full Name",
            'Category',
            'Gender',
            'PWD / Def',
            'EWS',
            'TFWS',
            'Orphan',
            'Minority Type (LM/RM)',
            'Merit Exam',
            'Percentile/Mark',
            'MHT-CET Math Percentile',
            'MHT-CET Physics Percentile',
            'MHT-CET Chemistry Percentile',
            'HSC PCM %',
            'HSC Math %',
            'HSC Physics %',
            'HSC / Diploma / D.Voc. Total %',
            'SSC Total %',
            'SSC Math %',
            'SSC Science %',
            'SSC English %'
        ]
    lines = csv_content.split('\n')
    modified_content = ','.join(column_names) + '\n'  # Add column names
    for i, line in enumerate(lines[1:], start=1):
        if line.strip():  # Skip empty lines
            modified_content += f'{i},{line}\n'  # Add serial number
    return modified_content

@app.route('/view_csv/<filename>')
def view_csv(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash(f"CSV file '{filename}' not found.")
        return redirect(url_for('index'))

    try:
        with open(file_path, 'r', newline='') as file:
            csv_content = file.read()
    except OSError:
        flash(f"Error reading CSV file '{filename}'.")
        return redirect(url_for('index'))

    # Modify CSV content to add serial number
    modified_csv_content = add_serial_number(csv_content,filename)

    return modified_csv_content

@app.route('/download_csv/<filename>')
def download_csv(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        # Modify CSV content to add serial number
        with open(file_path, 'r', newline='') as file:
            csv_content = file.read()
        modified_csv_content = add_serial_number(csv_content,filename)

        # Send modified CSV content as a file
        return send_file(
            io.BytesIO(modified_csv_content.encode()),
            mimetype='text/csv',
            as_attachment=True,  # Specify as_attachment=True to force download
            download_name=f"{filename.replace('.csv', '_modified.csv')}"  # Specify download filename here
        )
    else:
        return f"File '{filename}' not found.", 404
    
@app.route('/submit', methods=['POST'])
def submit():
    # Get user email from session
    user_email = session.get('email')
    user_id = session.get('query')

    if not user_email:
        flash('Email not found.')
        return redirect(url_for('index'))

    # Get the form data
    name = request.form.get('name')
    application_id = request.form.get('application_id')
    comment = request.form.get('comment')  # Assuming you have a comment field in your form

    # Define the path to the CSV file where submissions will be stored
    submissions_file = os.path.join(app.config['UPLOAD_FOLDER'], 'discrepancies.csv')

    # Append the submission data to the CSV file
    with open(submissions_file, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write the header only if the file is empty
        if csvfile.tell() == 0:
            writer.writerow(['Application ID', 'Name', 'Email', 'Comment'])  # CSV header
        writer.writerow([application_id, name, user_email, comment])  # CSV data

    # Create a confirmation message
    msg = Message("Confirmation of Submission", recipients=[user_email])
    msg.body = f"Dear {user_id},\n\nWe are pleased to inform you that your details have been successfully verified and submitted.\nYou are now registered for Spot Round 2024-25. \nThank you for your participation.\n\nIf you have any queries, please contact the college. \n\n\nBest regards,\nModern Education Society's Wadia College of Engineering.\n\nTelephone : (020)-26163831\nAdmission Enquiry : +91 7798883400\nEmail : info@mescoepune.org"
    mail.send(msg)

    # Render the submitted.html template
    return render_template('submitted.html')


if __name__ == '__main__':
    app.run(debug=True)
