from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from supabase import create_client, Client
import google.generativeai as genai
import threading
import time
from queue import Queue
import re
import random
import uuid
import logging
import os  # For directory management
from reportlab.lib.pagesizes import A4  # For PDF generation
from reportlab.pdfgen import canvas  # For PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from textwrap import wrap
import textwrap
import os

from textwrap import wrap  # For text wrapping

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Replace with your own secret key

# Supabase configuration for authentication only
supabase_url = "https://wzwhteyvzjebvcoqhuus.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6d2h0ZXl2emplYnZjb3FodXVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjMyODA1MDMsImV4cCI6MjAzODg1NjUwM30.fO1WEQOXSkvnKu36tI_vy1j3x-4HLWxGn53O5U_wGK8"
supabase: Client = create_client(supabase_url, supabase_key)

# Configure the Google Generative AI API
genai.configure(api_key="AIzaSyAbDhDeGHZcQNpoCA1BtAN8DWq7tDQif00")

# Create the model configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

diagnosis_queue = Queue()  # No maximum size for the queue
used_questions = set()  # Track used questions
generate_flag = threading.Event()  # Event flag to control the generation process

# Initialize the global correct_answers variable
correct_answers = 0

# Set up logging
logging.basicConfig(filename='diagnosis_queue.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Directory for saving PDFs
pdf_directory = "./diagnosis_pdfs/"
if not os.path.exists(pdf_directory):
    os.makedirs(pdf_directory)



from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
from textwrap import wrap

def generate_pdfs(diagnosis):
    """
    Generate two PDFs for the given diagnosis:
    - One with the correct answer included (in 'with_answers' folder)
    - One without the correct answer (in 'without_answers' folder)
    """
    # Extract diagnosis details
    patient_details = diagnosis.get("Patient Details", "N/A")
    present_symptoms = diagnosis.get("Present Symptoms", "N/A")
    physical_exam = diagnosis.get("Physical Exam", "N/A")
    lab_results = diagnosis.get("Lab Results", "N/A")
    imaging = diagnosis.get("Imaging", "N/A")
    options = diagnosis.get("options", [])
    correct_answer = diagnosis.get("correct_answer", "N/A")

    # Create the folders if they don't exist
    base_folder = os.getcwd()
    with_answers_folder = os.path.join(base_folder, "with_answers")
    without_answers_folder = os.path.join(base_folder, "without_answers")
    os.makedirs(with_answers_folder, exist_ok=True)
    os.makedirs(without_answers_folder, exist_ok=True)

    # Determine file numbering
    existing_files = [f for f in os.listdir(with_answers_folder) if f.endswith(".pdf")]
    next_file_number = len(existing_files) + 1

    # File paths
    with_answers_path = os.path.join(with_answers_folder, f"{next_file_number}.pdf")
    without_answers_path = os.path.join(without_answers_folder, f"{next_file_number}.pdf")

    # Generate both PDFs
    '''
    create_pdf(diagnosis, with_answers_path, include_correct_answer=True)
    create_pdf(diagnosis, without_answers_path, include_correct_answer=False)
'''
    return with_answers_path, without_answers_path



from math import ceil
from textwrap import wrap
'''
def create_pdf(diagnosis, file_path, include_correct_answer):
    """
    Create a single PDF with or without the correct answer based on the flag.
    """
    patient_details = diagnosis.get("Patient Details", "N/A")
    present_symptoms = diagnosis.get("Present Symptoms", "N/A")
    physical_exam = diagnosis.get("Physical Exam", "N/A")
    lab_results = diagnosis.get("Lab Results", "N/A")
    imaging = diagnosis.get("Imaging", "N/A")
    options = diagnosis.get("options", [])
    correct_answer = diagnosis.get("correct_answer", "N/A")

    # Create the PDF
    pdf_canvas = canvas.Canvas(file_path, pagesize=A5)
    width, height = A5
    margin = 50  # 20mm margin for all sides
    bottom_margin = 50  # Define a bottom margin
    usable_width = width - 2 * margin
    y_position = height - margin

    # Define the sections, their colors, and content
    sections = [
        ("Patient Details", patient_details, "#f4904c", add_wrapped_text_without_dot_bullet_points),
        ("Present Symptoms", present_symptoms, "#11c2c4", add_wrapped_text_with_bullet_points_presentsymp),
        ("Physical Exam", physical_exam, "#ff5757", add_wrapped_text_with_bullet_points_physicalex),
        ("Lab Results", lab_results, "#004aad", add_wrapped_text_with_bullet_points_sectionlabres),
        ("Imaging", imaging, "#8c52ff", add_wrapped_text_with_bullet_points_sectionimage),
    ]

    # Draw each section
    for title, content, color, wrapping_function in sections:
        if y_position < bottom_margin + 50:  # Ensure space above the bottom margin
            pdf_canvas.showPage()
            y_position = height - margin

        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.setFillColor(colors.HexColor(color))
        pdf_canvas.drawString(margin, y_position, f"{title}:")
        y_position -= 15
        pdf_canvas.setFillColor(colors.black)
        y_position = wrapping_function(
            pdf_canvas,
            content,
            margin,
            y_position,
            max_width=usable_width,
            font="Helvetica",
            font_size=10,
            leading=12
        )
        y_position -= 30  # Adjust space between sections

    # Move to the second page for options
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(margin, y_position, "Diagnosis Options:")
    y_position -= 15

    for option in options:
        # Calculate the height needed for the box
        font_size = 10
        leading = 12
        wrapped_option = wrap(option, width=int(usable_width / (font_size * 0.5)))
        box_height = len(wrapped_option) * leading + 20  # Add some padding

        if y_position - box_height < bottom_margin:  # Ensure space for bottom margin
            pdf_canvas.showPage()
            y_position = height - margin

        pdf_canvas.setFillColor(colors.white)
        pdf_canvas.rect(margin, y_position - box_height, usable_width, box_height, fill=1)
        pdf_canvas.setFillColor(colors.black)

        text_y = y_position - 20
        for line in wrapped_option:
            pdf_canvas.drawString(margin + 10, text_y, line)
            text_y -= leading

        y_position -= box_height + 10

    # Add correct answer if flag is set
    if include_correct_answer:
        if y_position - 50 < bottom_margin:  # Ensure space for bottom margin
            pdf_canvas.showPage()
            y_position = height - margin

        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(margin, y_position, "Correct Answer:")
        y_position -= 20
        pdf_canvas.setFont("Helvetica", 10)
        y_position = add_wrapped_text(
            pdf_canvas,
            correct_answer,
            margin,
            y_position,
            max_width=usable_width,
            font="Helvetica",
            font_size=10,
            leading=12
        )

    # Save the PDF
    pdf_canvas.save()



def add_wrapped_text(pdf_canvas, text, x, y, max_width, font="Helvetica", font_size=10, leading=12):
    """
    Adds text to the PDF canvas with justified alignment.
    """
    pdf_canvas.setFont(font, font_size)
    wrapped_lines = wrap(text, width=int(max_width / (font_size * 0.5)))

    for line in wrapped_lines[:-1]:  # Justify all lines except the last one
        words = line.split()
        num_gaps = len(words) - 1
        if num_gaps > 0:
            total_text_width = sum(pdf_canvas.stringWidth(word, font, font_size) for word in words)
            space_width = (max_width - total_text_width) / num_gaps
            x_pos = x
            for word in words[:-1]:
                pdf_canvas.drawString(x_pos, y, word)
                x_pos += pdf_canvas.stringWidth(word, font, font_size) + space_width
            pdf_canvas.drawString(x_pos, y, words[-1])  # Last word in the line
        else:
            pdf_canvas.drawString(x, y, line)  # Single-word line
        y -= leading

    # Last line is left-aligned
    if wrapped_lines:
        pdf_canvas.drawString(x, y, wrapped_lines[-1])
        y -= leading

    return y

def add_wrapped_text_without_dot_bullet_points(pdf_canvas, text, x, y, max_width, font="Helvetica", font_size=10, leading=12):
    pdf_canvas.setFont(font, font_size)
    lines = text.split("\n")
    first_line = True  # Track if it's the first line
    space_after_bullet = " "  # Single space after the bullet
    bullet_width = pdf_canvas.stringWidth("•" + space_after_bullet, font, font_size)  # Width of bullet + space

    for line in lines:
        wrapped_lines = wrap(line.strip(), width=int((max_width - bullet_width) / (font_size * 0.5)))
        for wrapped_line in wrapped_lines:
            if first_line:  # Add bullet to the first line
                pdf_canvas.setFillColor(colors.HexColor("#f4904c"))  # Orange bullet
                pdf_canvas.drawString(x, y, "•")
                pdf_canvas.setFillColor(colors.black)  # Reset to black for text
                pdf_canvas.drawString(x + bullet_width, y, wrapped_line)  # Align text after bullet
                first_line = False
            else:
                pdf_canvas.drawString(x + bullet_width, y, wrapped_line)  # Align wrapped lines left with the text
            y -= leading
    return y


from textwrap import wrap
from reportlab.lib.colors import HexColor
def add_wrapped_text_with_bullet_points_presentsymp(
    pdf_canvas, text, x, y, max_width, font="Helvetica", font_size=10, leading=12, bullet_color=HexColor('#11c2c4')
):
    """
    Adds text to the PDF canvas with bullet points, a small gap between the bullet and the text,
    and a bullet color based on the section.

    Parameters:
    - pdf_canvas: The canvas object to draw the text on.
    - text: The input text with each bullet as a separate line.
    - x: The x-coordinate where the text block starts.
    - y: The y-coordinate where the text block starts.
    - max_width: The maximum width for the text block.
    - font: The font to use for the text.
    - font_size: The font size for the text.
    - leading: The line spacing (distance between lines).
    - bullet_color: The color for the bullet points (default is blue).

    Returns:
    - y: The updated y-coordinate after rendering the text.
    """
    pdf_canvas.setFont(font, font_size)  # Set the font and size
    bullet = "•"  # Define the bullet symbol
    bullet_width = pdf_canvas.stringWidth(bullet, font, font_size)  # Calculate bullet width
    

    # Split text into lines based on bullet points
    lines = text.strip().split("\n")
      # Trim extra spaces and split at line breaks

    for line in lines:
        # Add the bullet and wrap the line within max_width
        line_content = line.strip()  # Remove extra spaces around the line
        wrapped_lines = wrap(
            line_content, width=int((max_width - bullet_width) / (font_size * 0.5))
        )  # Wrap text within width considering the bullet width

        for i, wrapped_line in enumerate(wrapped_lines):
            if i == 0:  # First line of the paragraph (includes the bullet)
                pdf_canvas.setFillColor(bullet_color)  # Set bullet color
                pdf_canvas.drawString(x, y, bullet)  # Draw the bullet
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)  # Draw the text with a gap after the bullet
            else:  # Subsequent lines are aligned to the start of the text
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for the text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)

            y -= leading  # Move to the next line
            

    return y

def add_wrapped_text_with_bullet_points_physicalex(
    pdf_canvas, text, x, y, max_width, font="Helvetica", font_size=10, leading=12, bullet_color=HexColor('#ff5757')
):
    """
    Adds text to the PDF canvas with bullet points, a small gap between the bullet and the text,
    and a bullet color based on the section.

    Parameters:
    - pdf_canvas: The canvas object to draw the text on.
    - text: The input text with each bullet as a separate line.
    - x: The x-coordinate where the text block starts.
    - y: The y-coordinate where the text block starts.
    - max_width: The maximum width for the text block.
    - font: The font to use for the text.
    - font_size: The font size for the text.
    - leading: The line spacing (distance between lines).
    - bullet_color: The color for the bullet points (default is blue).

    Returns:
    - y: The updated y-coordinate after rendering the text.
    """
    pdf_canvas.setFont(font, font_size)  # Set the font and size
    bullet = "•"  # Define the bullet symbol
    bullet_width = pdf_canvas.stringWidth(bullet, font, font_size)  # Calculate bullet width
    

    # Split text into lines based on bullet points
    lines = text.strip().split("\n")
      # Trim extra spaces and split at line breaks

    for line in lines:
        # Add the bullet and wrap the line within max_width
        line_content = line.strip()  # Remove extra spaces around the line
        wrapped_lines = wrap(
            line_content, width=int((max_width - bullet_width) / (font_size * 0.5))
        )  # Wrap text within width considering the bullet width

        for i, wrapped_line in enumerate(wrapped_lines):
            if i == 0:  # First line of the paragraph (includes the bullet)
                pdf_canvas.setFillColor(bullet_color)  # Set bullet color
                pdf_canvas.drawString(x, y, bullet)  # Draw the bullet
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)  # Draw the text with a gap after the bullet
            else:  # Subsequent lines are aligned to the start of the text
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for the text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)

            y -= leading  # Move to the next line
            

    return y

def add_wrapped_text_with_bullet_points_sectionlabres(
    pdf_canvas, text, x, y, max_width, font="Helvetica", font_size=10, leading=12,
    bullet_color=HexColor('#004aad'), bottom_margin=50
):
    """
    Adds text to the PDF canvas with bullet points, ensuring it respects the bottom margin.
    """
    pdf_canvas.setFont(font, font_size)  # Set the font and size
    bullet = "•"  # Define the bullet symbol
    bullet_width = pdf_canvas.stringWidth(bullet, font, font_size)  # Calculate bullet width
    page_height = pdf_canvas._pagesize[1]  # Get the height of the current page

    # Split text into lines based on bullet points
    lines = text.strip().split("\n")  # Trim extra spaces and split at line breaks

    for line in lines:
        # Add the bullet and wrap the line within max_width
        line_content = line.strip()  # Remove extra spaces around the line
        wrapped_lines = wrap(
            line_content, width=int((max_width - bullet_width) / (font_size * 0.5))
        )  # Wrap text within width considering the bullet width

        for i, wrapped_line in enumerate(wrapped_lines):
            if y - leading < bottom_margin:  # Check if there's enough space
                pdf_canvas.showPage()  # Start a new page
                y = page_height - 50  # Reset y to the top with margin
                pdf_canvas.setFont(font, font_size)  # Reset font after new page

            if i == 0:  # First line of the paragraph (includes the bullet)
                pdf_canvas.setFillColor(bullet_color)  # Set bullet color
                pdf_canvas.drawString(x, y, bullet)  # Draw the bullet
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)  # Draw the text with a gap after the bullet
            else:  # Subsequent lines are aligned to the start of the text
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for the text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)

            y -= leading  # Move to the next line

    return y

def add_wrapped_text_with_bullet_points_sectionimage(
    pdf_canvas, text, x, y, max_width, font="Helvetica", font_size=10, leading=12, bullet_color=HexColor('#8c52ff')
):
    """
    Adds text to the PDF canvas with bullet points, a small gap between the bullet and the text,
    and a bullet color based on the section.

    Parameters:
    - pdf_canvas: The canvas object to draw the text on.
    - text: The input text with each bullet as a separate line.
    - x: The x-coordinate where the text block starts.
    - y: The y-coordinate where the text block starts.
    - max_width: The maximum width for the text block.
    - font: The font to use for the text.
    - font_size: The font size for the text.
    - leading: The line spacing (distance between lines).
    - bullet_color: The color for the bullet points (default is blue).

    Returns:
    - y: The updated y-coordinate after rendering the text.
    """
    pdf_canvas.setFont(font, font_size)  # Set the font and size
    bullet = "•"  # Define the bullet symbol
    bullet_width = pdf_canvas.stringWidth(bullet, font, font_size)  # Calculate bullet width

    # Split text into lines based on bullet points
    lines = text.strip().split("\n")  # Trim extra spaces and split at line breaks

    for line in lines:
        # Add the bullet and wrap the line within max_width
        line_content = line.strip()  # Remove extra spaces around the line
        wrapped_lines = wrap(
            line_content, width=int((max_width - bullet_width) / (font_size * 0.5))
        )  # Wrap text within width considering the bullet width

        for i, wrapped_line in enumerate(wrapped_lines):
            if i == 0:  # First line of the paragraph (includes the bullet)
                pdf_canvas.setFillColor(bullet_color)  # Set bullet color
                pdf_canvas.drawString(x, y, bullet)  # Draw the bullet
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)  # Draw the text with a gap after the bullet
            else:  # Subsequent lines are aligned to the start of the text
                pdf_canvas.setFillColor(HexColor(0x000000))  # Reset to black for the text
                pdf_canvas.drawString(x + bullet_width + 2, y, wrapped_line)

            y -= leading  # Move to the next line

    return y
'''

def generate_diagnosis():
    medical_prompt = """
    Create a medical diagnosis case for a medical student. Include the following sections: Patient Details, Present Symptoms, Physical Exam, Lab Results, and Imaging. Use Bangladeshi names for the Patient Details section.
    
    Additionally:
    1. Provide four diagnostic options, one of which is the correct diagnosis. Do not number the options.
    2. Provide a detailed explanation for why the correct diagnosis is correct, including clinical presentation, physical exam findings, and laboratory findings.
    3. Provide explanations for why the other diagnoses are less likely, addressing key clinical, lab, or imaging findings that rule them out.
    """

    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(medical_prompt)
    diagnosis_text = response.text.replace('*', '')  # Remove "*" symbols from generated text
    
    # Extract sections using regex
    sections = {
        "Patient Details": format_section(extract_section(diagnosis_text, "Patient Details")),
        "Present Symptoms": format_section(extract_section(diagnosis_text, "Present Symptoms")),
        "Physical Exam": format_section(extract_section(diagnosis_text, "Physical Exam")),
        "Lab Results": format_section(extract_section(diagnosis_text, "Lab Results")),
        "Imaging": format_section(extract_section(diagnosis_text, "Imaging")),
    }

    # Extract diagnosis options and explanations
    options = extract_options(diagnosis_text)
    correct_answer = options[0] if options else "No correct answer found"
    explanations = {
        "correct": extract_section(diagnosis_text, "Why the Correct Diagnosis is Correct"),
        "other": extract_section(diagnosis_text, "Why the Other Diagnoses are Less Likely"),
    }
    

    # Shuffle options to randomize correct answer position
    random.shuffle(options)

    sections.update({
        'correct_answer': correct_answer,
        'options': options,
        'explanations': explanations,
        'medical_code': generate_medical_code()  # Generate medical code
    })

    # Generate PDF file for the diagnosis case
    pdf_file_path = generate_pdfs(sections)
    logging.info(f"PDF file generated and saved at: {pdf_file_path}")

    return sections


def extract_section(text, section_name):
    """ Extract a specific section from the diagnosis text based on section name """
    pattern = re.compile(rf"{section_name}:?\s*(.*?)(?=\n\n|\Z)", re.DOTALL | re.IGNORECASE)
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return "No data available."


def extract_options(text):
    """ Extract diagnostic options from the generated text """
    options_pattern = re.compile(r"Options:?\s*(.*?)(?=\n\n|\Z)", re.DOTALL | re.IGNORECASE)
    match = re.search(options_pattern, text)
    if match:
        options_text = match.group(1).strip()
        options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
        return options
    return []

def format_section(text):
    """ Format the extracted section into subpoints """
    return "\n".join(line.strip() for line in text.split('\n') if line.strip())

def generate_medical_code():
    """ Generate a unique medical code """
    return str(uuid.uuid4())[:8]  # Example: Generate an 8-character alphanumeric code


def fill_diagnosis_pool():
    while True:
        if diagnosis_queue.qsize() < 8:  # If the queue has less than 8 cases
            diagnosis = generate_diagnosis()
            diagnosis_text = str(diagnosis)  # Convert to string for hashability
            if diagnosis_text not in used_questions:  # Avoid duplicates
                diagnosis_queue.put(diagnosis)  # Add the new diagnosis to the queue
                used_questions.add(diagnosis_text)  # Track the used questions
                logging.info(f"Added new diagnosis. Queue size: {diagnosis_queue.qsize()}")
        else:
            logging.info(f"Queue is full. Current size: {diagnosis_queue.qsize()}")
        
        # Sleep for a short while to avoid consuming too many resources in the infinite loop
        time.sleep(1)

@app.route('/')
def index1():
    return render_template('index1.html')
    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        response = supabase.auth.sign_up({
            'email': email,
            'password': password,
        })
        
        if response.get('error'):
            flash('Sign-up failed: ' + response['error']['message'], 'danger')
        else:
            flash('Sign-up successful! Check your email for confirmation.', 'success')
        return redirect(url_for('index1'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Sign in with Supabase
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        # Check for errors in the response
        if hasattr(response, 'error') and response.error:
            flash('Login failed: ' + response.error.message, 'danger')
        else:
            # Save user data in session
            session['user_id'] = response.user.id
            flash('Login successful! Welcome back.', 'success')
            # Redirect to the diagnosis page
            return redirect(url_for('index'))
    
    return render_template('login.html')


@app.route('/diagnosis')
def index():
    # This route should trigger the diagnostic generation
    # Ensure that the generation logic is in place and functional
    return render_template('index.html')

@app.route('/progress_page')
def progress_page():
    return render_template('progress.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

# Modify the /generate route to serve cases in sequence
@app.route('/generate')
def generate():
    if not diagnosis_queue.empty():  # Check if the queue is not empty
        # Get the next diagnosis from the queue
        diagnosis = diagnosis_queue.get()

        # Return the diagnosis along with its sequence number
        diagnosis_text = str(diagnosis)
        used_questions.add(diagnosis_text)
        logging.info(f"Generated diagnosis case. Queue size: {diagnosis_queue.qsize()}")
        return jsonify(diagnosis)  # Send the diagnosis as a JSON response
    else:
        return jsonify({"error": "Diagnosis queue is empty. Please try again later."})

@app.route('/solved', methods=['POST'])
def solved():
    global correct_answers
    correct_answers += 1
    logging.info(f"Correct answers: {correct_answers}")
    
    # Add the logic to handle level progression
    if correct_answers % 10 == 0:  # Example: Every 10 correct answers progresses the user to the next level
        return jsonify({"message": "Congratulations! You've advanced to the next level!", "next_level": True})
    
    return jsonify({"message": "Correct diagnosis!", "next_level": False})

@app.route('/get_progress')
def get_progress():
    global correct_answers
    achievements = []
    if correct_answers >= 10:
        achievements.append({"name": "Novice Diagnostician", "description": "Correctly diagnosed 10 cases."})
    if correct_answers >= 50:
        achievements.append({"name": "Intermediate Diagnostician", "description": "Correctly diagnosed 50 cases."})
    if correct_answers >= 100:
        achievements.append({"name": "Expert Diagnostician", "description": "Correctly diagnosed 100 cases."})

    return jsonify({"correct_answers": correct_answers, "achievements": achievements})

@app.before_request
def prevent_back_button():
    # Prevent users from navigating back to previous questions
    if request.method == 'POST' and request.path == '/solved':
        session.modified = True

if __name__ == "__main__":
    # Start the background thread to keep generating diagnosis cases
    generate_thread = threading.Thread(target=fill_diagnosis_pool)
    generate_thread.daemon = True  # This ensures the thread will exit when the main program exits
    generate_thread.start()
    

    app.run(debug=True, threaded=True,host='0,0,0,0:8080')
