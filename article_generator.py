import os
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

import wikipediaapi

# === Flask App Setup ===
app = Flask(__name__)
UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}

# === Set your OpenAI API key ===
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")  # Make sure this is set


# === Helper Functions ===

def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def load_documents(files):
    documents = []
    for file in files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        ext = os.path.splitext(filename)[1].lower()
        if ext == '.pdf':
            loader = PyPDFLoader(filepath)
        elif ext == '.docx':
            loader = Docx2txtLoader(filepath)
        elif ext == '.txt':
            loader = TextLoader(filepath)
        else:
            continue

        documents.extend(loader.load())
    return documents


def fetch_wikipedia_article(topic):
    wiki = wikipediaapi.Wikipedia("en")
    page = wiki.page(topic)
    return page.summary if page.exists() else ""


def create_retriever(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(chunks, embeddings)
    return vectorstore.as_retriever()


def generate_article(topic, retriever):
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)

    prompt_template = f"""
You are an experienced journalist for a newspaper.
Write a detailed, well-structured newspaper article on the topic: "{topic}".

Base the article on the retrieved context provided to you.

Output format:
Headline: <a concise headline>
Content: <formal article content in 3–5 short paragraphs>
"""

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=False
    )

    response = qa_chain.run(prompt_template)
    lines = response.strip().split('\n')
    headline = lines[0].replace("Headline:", "").strip()
    content = '\n'.join(lines[1:]).replace("Content:", "").strip()

    return headline, content


# === Flask Route ===
@app.route("/generate", methods=["POST"])
def generate():
    topic = request.form.get("topic", "").strip()
    use_wikipedia = request.form.get("use_wikipedia") == "true"
    uploaded_files = request.files.getlist("files")

    if not topic:
        return jsonify({"error": "Topic is required."}), 400

    try:
        documents = []

        if use_wikipedia:
            wiki_text = fetch_wikipedia_article(topic)
            if wiki_text:
                from langchain.schema import Document
                documents.append(Document(page_content=wiki_text))

        if uploaded_files:
            docs_from_files = load_documents(uploaded_files)
            documents.extend(docs_from_files)

        if not documents:
            return jsonify({"error": "No context provided from files or Wikipedia."}), 400

        retriever = create_retriever(documents)
        headline, content = generate_article(topic, retriever)

        return jsonify({
            "headline": headline,
            "content": content,
            "full_article": f"{headline}\n\n{content}"
        })

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# === Run Server ===
if __name__ == "__main__":
    app.run(debug=True)
