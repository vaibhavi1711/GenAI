from flask import Flask, render_template, request, jsonify
import os
import tempfile
from werkzeug.utils import secure_filename
import article_generator

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_article():
    topic = request.form.get('topic')
    if not topic:
        return jsonify({"error": "Please provide a topic"}), 400
    
    use_wikipedia = request.form.get('use_wikipedia') == 'true'
    
    # Process uploaded files if any
    uploaded_files = []
    if 'files' in request.files:
        files = request.files.getlist('files')
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_files.append(filepath)
    
    try:
        article = article_generator.generate_newspaper_article(
            topic=topic,
            use_wikipedia=use_wikipedia,
            file_paths=uploaded_files
        )
        
        # Clean up uploaded files
        for filepath in uploaded_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Parse headline and content
        lines = article.strip().split('\n')
        headline = lines[0].replace("HEADLINE:", "").strip()
        content = "\n".join(lines[1:]).strip()
        
        return jsonify({
            "success": True,
            "headline": headline,
            "content": content,
            "full_article": article
        })
    
    except Exception as e:
        # Clean up uploaded files in case of error
        for filepath in uploaded_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)