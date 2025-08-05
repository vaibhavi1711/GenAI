import os
from dotenv import load_dotenv
load_dotenv()

import tempfile
from flask import Flask, request, jsonify
import wikipediaapi
from PyPDF2 import PdfReader
import docx
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

app = Flask(__name__)

# Initialize Wikipedia API
wiki = wikipediaapi.Wikipedia(
    language="en",
    user_agent="GenAIProjectBot/1.0 (vaibhavirane2000@example.com)"
)


# Load OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

# Initialize OpenAI LLM wrapper
llm = OpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)

def extract_text_from_pdf(file_path):
    text = []
    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extract_text_from_file(file_storage):
    # Save to temp file for processing
    suffix = os.path.splitext(file_storage.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        file_storage.save(tmp.name)
        if suffix == ".pdf":
            return extract_text_from_pdf(tmp.name)
        elif suffix == ".docx":
            return extract_text_from_docx(tmp.name)
        elif suffix == ".txt":
            return extract_text_from_txt(tmp.name)
        else:
            return ""

def get_wikipedia_text(topic):
    page = wiki.page(topic)
    if page.exists():
        # Return summary + full text fallback (limit for sanity)
        return page.summary + "\n\n" + page.text[:2000]
    else:
        return ""

def create_chroma_index(documents, embeddings):
    # documents is a list of strings
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = []
    for doc in documents:
        docs.extend(text_splitter.split_text(doc))
    return Chroma.from_texts(docs, embeddings)

@app.route("/generate", methods=["POST"])
def generate_article():
    try:
        topic = request.form.get("topic", "").strip()
        use_wikipedia = request.form.get("use_wikipedia", "false").lower() == "true"
        files = request.files.getlist("files")

        if not topic:
            return jsonify({"error": "Topic is required."}), 400

        # Gather context documents text
        context_texts = []

        # Extract text from uploaded files
        for file in files:
            text = extract_text_from_file(file)
            if text:
                context_texts.append(text)

        # Add Wikipedia text if requested
        if use_wikipedia:
            wiki_text = get_wikipedia_text(topic)
            if wiki_text:
                context_texts.append(wiki_text)

        if not context_texts:
            # Fallback: just use Wikipedia summary or topic prompt
            wiki_text = get_wikipedia_text(topic)
            if wiki_text:
                context_texts.append(wiki_text)
            else:
                context_texts.append(f"Write a newspaper article about {topic}.")

        # Build embedding and vector store
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = create_chroma_index(context_texts, embeddings)

        # Create retrieval QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(),
            return_source_documents=False
        )

        prompt = f"Write a concise, well-structured newspaper article about the topic: {topic}. Use the retrieved information to support your writing."

        # Run chain
        answer = qa_chain.run(prompt)

        # Prepare headline (simple approach: first line or generate with LLM)
        headline_prompt = f"Write a catchy newspaper headline for an article about: {topic}"
        headline = llm.call_as_llm([{"role": "user", "content": headline_prompt}]).strip()

        return jsonify({
            "headline": headline,
            "content": answer,
            "full_article": f"{headline}\n\n{answer}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
