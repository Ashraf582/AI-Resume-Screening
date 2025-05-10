from flask import Flask, render_template_string, request
import os
import fitz  # PyMuPDF
import difflib
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

job_descriptions = {
    'Data Scientist': "Experience with machine learning, Git and GitHub, Leadership, Python, Python basics, data analysis, statistics, and data visualization. Knowledge of data wrangling, model evaluation, and deployment.",
    'Web Developer': "Proficient in HTML, CSS, JavaScript, React or Angular, backend APIs, RESTful services, and SQL/NoSQL databases. Understanding of responsive design and version control.",
    'Android Developer': "Strong knowledge of Java/Kotlin, Android SDK, UI/UX principles, and experience publishing apps on Google Play Store. Familiarity with Jetpack, MVVM, and Firebase.",
    'DevOps Engineer': "Experience with CI/CD pipelines, Docker, Kubernetes, cloud platforms (AWS/Azure/GCP), monitoring, and scripting (Bash, Python).",
    'Cybersecurity Analyst': "Knowledge of network security, firewalls, intrusion detection systems, ethical hacking, vulnerability assessments, and incident response.",
    'AI/ML Engineer': "Expertise in machine learning frameworks like TensorFlow, PyTorch. Strong Python skills, model deployment, deep learning, and NLP experience."
}

thresholds = {
    'hard': 0.05,
    'medium': 0.035,
    'easy': 0.02
}

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
<title>AI Resume Screening</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style> body {
font-family: 'Inter', sans-serif; background: #121212;
color: #f1f1f1; padding: 40px;
}
.container {
max-width: 900px; margin: auto; background: #1e1e1e; padding: 40px; border-radius: 12px;
box-shadow: 0 0 20px rgba(0,0,0,0.3);
}
h1 {
text-align: center; margin-bottom: 30px; font-size: 32px; color: #ffffff;
}
.form-group {
margin-bottom: 20px;
}
label {
font-weight: 600; display: block; margin-bottom: 8px;
 
}
input[type="file"], select { width: 100%;
padding: 10px; font-size: 16px;
background: #2a2a2a; color: #f1f1f1;
border: 1px solid #333;
}
button {
background: #0984e3; color: white;
padding: 12px 25px; font-size: 16px; border: none;
border-radius: 6px; cursor: pointer; display: block; margin: 20px auto 0;
}
button:hover { background: #0652dd;
}
</style>
</head>
<body>
<div class="container">
<h1>AI Resume Screening</h1>
<form method="POST" action="/result" enctype="multipart/form-data">
<div class="form-group">
<label for="resumes">Upload Resumes (PDF Only)</label>
<input type="file" name="resumes" accept="application/pdf" multiple required>
</div>
<div class="form-group">
<label for="domain">Select Job Role</label>
<select name="domain" required>
{% for role in roles %}
<option value="{{ role }}">{{ role }}</option>{% endfor %}
 
</select>
</div>
<div class="form-group">
<label for="filter">Select Filter Level</label>
<select name="filter" required>
<option value="hard">High (Hard)</option>
<option value="medium">Medium</option>
<option value="easy">Low</option>
</select>
</div>
<button type="submit">Screen Resumes</button>
</form>
</div>
</body>
</html> """
 # Keep as is
RESULT_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Results - Resume Screening</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style> body {
background: #121212;
font-family: 'Inter', sans-serif; color: #f1f1f1;
padding: 40px;
}
.container {
max-width: 1000px; margin: auto; background: #1e1e1e; padding: 40px; border-radius: 12px;
box-shadow: 0 0 20px rgba(0,0,0,0.3);
}
h1 {
text-align: center; font-size: 30px;
margin-bottom: 20px;
}
.summary {
text-align: center; margin-bottom: 30px; font-size: 16px;
}
table {
width: 100%;
border-collapse: collapse;
}
th, td {
padding: 15px;
border-bottom: 1px solid #444;
}
th {
background: #2a2a2a; text-align: left;
}
.shortlisted { color: #2ecc71; font-weight: bold; }
.rejected { color: #e74c3c; font-weight: bold; }
.suggestions { font-size: 14px; color: #bbbbbb; }
</style>
</head>
<body>
<div class="container">
<h1>Screening Results</h1>
<div class="summary">
Job Role: <strong>{{ job_domain }}</strong> |
Filter Level: <strong>{{ filter_level.capitalize() }}</strong>
</div>
<table>
<tr>
<th>Candidate Name</th>
<th>Similarity Score</th>
<th>Status</th>
<th>Suggestions</th>
</tr>
{% for result in results %}
<tr>
<td>{{ result.name }}</td>
<td>{{ result.score }}</td>
<td class="{{ 'shortlisted' if result.status == 'Shortlisted' else 'rejected' }}">{{ result.status }}</td>
<td class="suggestions">{{ result.suggestions }}</td>
</tr>
{% endfor %}
</table>
</div>
</body>
</html>
"""

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text.lower()

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML, roles=job_descriptions.keys())

@app.route("/result", methods=["POST"])
def result():
    domain = request.form['domain']
    filter_level = request.form['filter']
    threshold = thresholds.get(filter_level, 0.035)
    job_description = job_descriptions[domain].lower()
    
    uploaded_files = request.files.getlist("resumes")
    results = []

    for resume in uploaded_files:
        filename = secure_filename(resume.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        resume.save(save_path)

        extracted_text = extract_text_from_pdf(save_path)
        similarity = difflib.SequenceMatcher(None, job_description, extracted_text).ratio()
        status = "Shortlisted" if similarity >= threshold else "Rejected"

        # Suggestions for rejected resumes
        suggestions = ""
        if status == "Rejected":
            job_keywords = set(job_description.split(','))
            resume_keywords = set(extracted_text.split())
            missing = job_keywords - resume_keywords
            suggestions = "Consider adding: " + ", ".join(list(missing)[:5])

        results.append({
            "name": filename,
            "score": f"{similarity:.2f}",
            "status": status,
            "suggestions": suggestions if suggestions else "N/A"
        })

    return render_template_string(RESULT_HTML, results=results, job_domain=domain, filter_level=filter_level)

if __name__ == "__main__":
    app.run(debug=True)
