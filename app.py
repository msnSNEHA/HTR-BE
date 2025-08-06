from flask import Flask, request, jsonify, render_template_string, redirect
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

DATA_FILE = 'data.json'
HTR_FILE = 'htr_counter.txt'
USED_LINKS_FILE = 'used_links.json'
MANAGER_EMAIL = 'snehamani7310@gmail.com'
SENDER_EMAIL = 'snehamani7310@gmail.com'
SENDER_PASSWORD = 'Sneha@2001'  # Replace with an app password or environment variable in production

# Initialize counter and data files
for file, default in [(HTR_FILE, 'HTR05237'), (DATA_FILE, {}), (USED_LINKS_FILE, {})]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump(default, f) if isinstance(default, dict) else f.write(default)

def get_next_htr_number():
    with open(HTR_FILE, 'r+') as f:
        last_htr = f.read().strip()
        num = int(last_htr[3:]) + 1
        next_htr = f"HTR{num:05d}"
        f.seek(0)
        f.write(next_htr)
        f.truncate()
    return next_htr

@app.route("/submit", methods=["POST"])
def submit_form():
    form_data = request.form.to_dict()
    submission_id = str(len(load_data()) + 1)
    save_submission(submission_id, form_data)

    # Generate review link
    review_link = f"{request.host_url}review/{submission_id}"
    send_email(MANAGER_EMAIL, "New HTR Submission", f"Please review here: {review_link}")

    return jsonify({"message": "Form submitted successfully.", "review_link": review_link})

@app.route("/review/<submission_id>")
def review(submission_id):
    used_links = load_used_links()
    if submission_id in used_links:
        return "❌ This review link has expired or already been used."

    data = load_data().get(submission_id)
    if not data:
        return "Submission not found."

    html = f"""
    <html><head><title>Review HTR</title></head><body>
    <h2>HTR Review for Submission {submission_id}</h2>
    <ul>
        {''.join(f'<li><strong>{k}</strong>: {v}</li>' for k, v in data.items())}
    </ul>
    <form action="/generate_htr/{submission_id}" method="POST">
        <button type="submit">Generate HTR Number</button>
    </form>
    </body></html>
    """
    return render_template_string(html)

@app.route("/generate_htr/<submission_id>", methods=["POST"])
def generate_htr(submission_id):
    used_links = load_used_links()
    if submission_id in used_links:
        return "❌ This link has already been used to generate an HTR number."

    data = load_data()
    if submission_id not in data:
        return "Submission not found."

    if "HTR Number" in data[submission_id]:
        return f"❌ HTR number already generated: {data[submission_id]['HTR Number']}"

    htr_number = get_next_htr_number()
    data[submission_id]["HTR Number"] = htr_number
    data[submission_id]["HTR Generated At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_all_data(data)

    # Mark the link as used
    used_links[submission_id] = True
    save_used_links(used_links)

    # Send confirmation email to user
    user_email = data[submission_id].get("Requestor_Email")
    user_name = data[submission_id].get("Name", "Requestor_Name")

    if user_email:
        subject = "Your HTR Number is Generated"
        body = f"Hello {user_name},\n\nYour HTR number has been successfully generated: {htr_number}"
        send_email(user_email, subject, body)

    return f"<h2>HTR Number Generated: {htr_number}</h2><br><strong>✅ This link has now expired.</strong>"

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_submission(submission_id, data):
    all_data = load_data()
    all_data[submission_id] = data
    save_all_data(all_data)

def save_all_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_used_links():
    with open(USED_LINKS_FILE, 'r') as f:
        return json.load(f)

def save_used_links(data):
    with open(USED_LINKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


