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
        uploaded_files = request.files.getlist("file")
        if not uploaded_files or all(
            uploaded.filename == ""
            for uploaded in uploaded_files
        ):
            return "Please choose one or more files.", 400
        document_parts = []
        filenames = []
        for uploaded in uploaded_files:
            if uploaded.filename == "":
                continue
            filename = secure_filename(uploaded.filename)
            extension = filename.rsplit(".", 1)[-1].lower()
            if extension in ("txt", "md", "py", "csv"):
                file_text = uploaded.read().decode(
                    "utf-8",
                    errors="replace"
                )

            elif extension == "pdf":
                reader = PdfReader(BytesIO(uploaded.read()))
                file_text = "\n".join(
                    page.extract_text() or ""
                    for page in reader.pages
                )

            else:
                return f"Unsupported file type: {filename}", 400

            if file_text.strip():
                filenames.append(filename)
                document_parts.append(
                    f"\n\n--- START OF FILE: {filename} ---\n\n"
                    f"{file_text}"
                    f"\n\n--- END OF FILE: {filename} ---"
                )

        if not document_parts:
            return "No readable text was found in the uploaded files.", 400

        all_file_text = "\n".join(document_parts)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Create a concise, student-friendly MCQ quiz directly "
                        "from the supplied documents. Do not use extended reasoning."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
Create 15 multiple-choice questions that cover all uploaded documents.

For each question, use exactly this format:

Question 1: ...
A. ...
B. ...
C. ...
D. ...
Answer: A
Explanation: One short sentence.

Uploaded files: {", ".join(filenames)}

Documents:
{all_file_text}
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
