from io import BytesIO
from flask import *
from werkzeug.utils import secure_filename
from openai import OpenAI
from waitress import serve
from pypdf import PdfReader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

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

        if not uploaded or uploaded.filename == "":
            return "Please choose a file.", 400

        filename = secure_filename(uploaded.filename)
        extension = filename.rsplit(".", 1)[-1].lower()

        if extension in ("txt", "md", "py", "csv"):
            file_text = uploaded.read().decode("utf-8", errors="replace")

        elif extension == "pdf":
            reader = PdfReader(BytesIO(uploaded.read()))
            file_text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        else:
            return "Please upload a TXT, Markdown, Python, CSV, or PDF file.", 400

        if not file_text.strip():
            return "No readable text was found in this file.", 400

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Create a concise, student-friendly MCQ quiz directly "
                        "from the supplied document. Do not use extended reasoning."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
Create 15 multiple-choice questions covering the entire document.

For each question, use this format:

Question 1: ...
A. ...
B. ...
C. ...
D. ...
Answer: A
Explanation: One short sentence.

Filename: {filename}

Document:
{file_text}
""",
                },
            ],
            temperature=0.2,
            max_tokens=1800,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
        )

        answer = response.choices[0].message.content

    return render_template("index.html", answer=answer)


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5001)
