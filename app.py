import io
import shutil
from flask import Flask, flash, render_template, request, redirect, send_file, url_for, send_from_directory, make_response
from werkzeug.utils import secure_filename
import os
import csv
import tabula
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# Set the upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set to keep track of uploaded file names
uploaded_files = set()

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

# Function to convert PDF to CSV
def pdf_to_csv(pdf_path, output_csv):
    # Initialize an empty list to store DataFrames
    all_dfs = []

    # Read the PDF file in batches
    for page_num in range(1, 5531, 50):  # Change 50 to an appropriate batch size
        end_page = min(page_num + 49, 5530)
        # Read PDF into DataFrame and append to the list
        df = tabula.read_pdf(pdf_path, pages=f"{page_num}-{end_page}", multiple_tables=True, lattice=True)
        all_dfs.extend(df)

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

        for file in files:
            # If user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file')
                return render_template('upload.html')

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename in uploaded_files:
                    flash('File has already been uploaded and converted')
                else:
                    uploaded_files.add(filename)  # Add filename to the set of uploaded files
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)

                    # Convert uploaded PDF to CSV
                    output = os.path.join(app.config['UPLOAD_FOLDER'], 'output1.csv' if len(uploaded_files) == 1 else 'output2.csv')
                    pdf_to_csv(file_path, output)

        # No need to redirect after successful upload, user stays on the page
        return render_template('upload.html')
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/search', methods=['GET', 'POST'])
def search():
    jee = "JEE"
    if request.method == 'POST':
        query = request.form['query']
        first_name = request.form['first_name'].upper()  # Convert first name to uppercase
        middle_name = request.form['middle_name'].upper()  # Convert middle name to uppercase
        last_name = request.form['last_name'].upper()  # Convert last name to uppercase
        mobile = request.form['mobile']
        email = request.form['email']
        department = request.form['department']  # Capture department from form data

        # Combine names into check_values for searching
        full_name = f"{first_name} {middle_name} {last_name}".strip()
        first_middle_name = f"{first_name} {middle_name}".strip()
        check_value = f"{first_name} {middle_name} {last_name}"

        # Search based on different scenarios
        results1 = search_data(full_name, 'output1.csv') if last_name else search_data(first_middle_name, 'output1.csv') if middle_name else search_data(first_name, 'output1.csv')
        results2 = search_data(full_name, 'output2.csv') if last_name else search_data(first_middle_name, 'output2.csv') if middle_name else search_data(first_name, 'output2.csv')

        # Flag to track if check value was found in any results
        check_found = bool(results1 or results2)

        # Basic email and mobile number validation (add more thorough validation if needed)
        if not email or not email.strip() or not mobile or not mobile.strip():
            flash('Please fill in all required fields (email, mobile number).')
            return render_template('search.html')  # Or redirect to appropriate page
        
        # Check if contact.csv exists
        contact_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contact.csv')
        if os.path.exists(contact_csv_path):
            # Check if the query exists in contact.csv for the same department
            with open(contact_csv_path, 'r', newline='') as contact_file:
                reader = csv.reader(contact_file)
                for row in reader:
                    if query == row[0]:
                        flash('Already applied')
                        return render_template('search.html',message_level=message_level)

        # Save searched data (if check value is found and result is from output1.csv with "JEE")
        jee_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'jee.csv')
        with open(jee_csv_path, 'a', newline='') as jee_file:
            writer = csv.writer(jee_file)
            # Write headers only if the file is empty
            if not results1 and not os.path.getsize(jee_csv_path):
                writer.writerow(results1[0].keys()) if results1 else None
            # Append data for each result (if check value is found and result is from output1.csv with "JEE")
            for row in results1:
                if any(jee == value for value in row.values()):  
                    if any(check_value == value for value in row.values()):
                        writer.writerow(row.values())
                        check_found = True
                        break  # Exit loop after finding check value


        # Similar logic for cet.csv
        cet_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cet.csv')
        with open(cet_csv_path, 'a', newline='') as cet_file:
            writer = csv.writer(cet_file)
            # Write headers only if the file is empty
            if not results2 and not os.path.getsize(cet_csv_path):
                writer.writerow(results2[0].keys()) if results2 else None
            # Append data for each result (if check value is found)
            for row in results2:
                if any(check_value == value for value in row.values()):
                    writer.writerow(row.values())
                    check_found = True
                    break

        # Save contact information only if check value was found
        if check_found:
            contact_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contact.csv')
            # Check if contact.csv exists, create it if not
            if not os.path.exists(contact_csv_path):
                with open(contact_csv_path, 'w', newline='') as contact_file:
                    writer = csv.writer(contact_file)
                    writer.writerow(['Application ID', 'Name','Department', 'Email', 'Mobile Number'])

            # Write to contact.csv only if check_found is True
            with open(contact_csv_path, 'a', newline='') as contact_file:
                writer = csv.writer(contact_file)
                writer.writerow([query, check_value,  department, email, mobile])  # Include department

                # Process records from output2.csv (cet.csv) and create separate CSV files
                if check_found:  # Only process if check value was found
                    for row in results2:
                        # Extract the value for filename
                        value_filename = row.get('Unnamed: 3', '')
                        value_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{value_filename}.csv")

                        with open(value_csv_path, 'a', newline='') as value_file:
                            writer = csv.writer(value_file)
                            # Write headers only if the file is empty
                            if not os.path.getsize(value_csv_path):
                                writer.writerow(row.keys())
                            writer.writerow(row.values())

                        # Apply sorting on the created value.csv file
                        sort_csv_file(value_csv_path)

            # Apply sorting on jee.csv and cet.csv based on the first column
            if results1:
                sort_csv_file(jee_csv_path)
            if results2:
                sort_csv_file(cet_csv_path)

            # Check if the check value was found in any results
            cross_checked = check_found

            # Return the template with search results and cross_checked flag
            return render_template('result.html', results_dict={'jee': results1, 'cet': results2}, cross_checked=cross_checked)
    return render_template('search.html')

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

        # Handle non-numeric values (choose a suitable approach)
        for i, row in enumerate(all_data):  # Use enumerate for row index
            try:
                row[0] = float(row[0])
            except ValueError:
                # Option 1: Skip the row (current behavior)
                all_data.pop(i)  # Remove the row with non-numeric value

                # Option 2: Assign a specific value (e.g., 0 or a placeholder)
                # row[0] = 0

        # Sort based on the first column (index 0) in ascending order
        all_data.sort(key=lambda row: float(row[0]) if row else 0)

        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(all_data)

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
            'Merit Exam',
            'Category',
            'Gender',
            'PWD / Def',
            'EWS',
            'TFWS',
            'Orphan',
            'Minority Type (LM/RM)',
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
    
    # Add serial numbers starting from 1 for the first row and 2 for subsequent rows
    for i, line in enumerate(lines):
        if line.strip():  # Skip empty lines
            if i == 0:
                modified_content += f'1,{line}\n'  # Add serial number 1 for the first row
            else:
                modified_content += f'{i+1},{line}\n'  # Add serial number starting from 2 for subsequent rows

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
    # Render the submitted.html template
    return render_template('submitted.html')


#if __name__ == '__main__':
 #   app.run(debug=True)
