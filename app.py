from flask import *
from werkzeug.utils import secure_filename
from openai import OpenAI
from waitress import serve
from io import BytesIO
from pypdf import PdfReader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)

MODEL = "prism-ml/bonsai-27b"

@app.route("/", methods=["GET", "POST"])
def index():
    answer = None

    if request.method == "POST":
        uploaded = request.files.get("file")

        filename = secure_filename(uploaded.filename)
        extension = filename.rsplit(".", 1)[-1].lower()

        if extension in ("txt", "md", "py", "csv"):
            file_text = uploaded.read().decode("utf-8", errors="replace")

        elif extension == "pdf":
            reader = PdfReader(BytesIO(uploaded.read()))
            file_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        else:
            return "Please upload a text, code, CSV, Markdown, or PDF file.", 400

        if not file_text.strip():
            return "No readable text was found in this file.", 400

        file_text = file_text[:50_000]  # keep within the model context limit

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise, helpful assistant. PLEASE BE FAST, RESPOND QUICKLY. AND BE CONCISE."
                },
                {
                    "role": "user",
                    "content": (
                        "Make a MCQ quiz out of the following file contents.\n\n"
                        f"Filename: {filename}\n\n"
                        f"File contents:\n{file_text}"
                    ),
                },
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content

    return render_template("index.html", answer=answer)

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5001)
