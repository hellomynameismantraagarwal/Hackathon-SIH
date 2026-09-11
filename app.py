import json
from io import BytesIO
import flask_bootstrap
from flask import Flask, request, render_template
from openai import OpenAI
from pypdf import PdfReader
from waitress import serve
from werkzeug.utils import secure_filename



with open('openrouterapikey.txt', 'r') as f:
    OPENROUTER_API_KEY = f.read().strip()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
flask_bootstrap.Bootstrap(app)

@app.route("/", methods=["GET", "POST"])
def index():
    quiz = None
    if request.method == "POST":
        uploaded_files = request.files.getlist("file")

        if not uploaded_files or all(uploaded.filename == "" for uploaded in uploaded_files):
            return "Please choose one or more files.", 400
        document_parts = []
        filenames = []
        for uploaded in uploaded_files:
            if uploaded.filename == "":
                continue
            filename = secure_filename(uploaded.filename)
            if "." not in filename:
                return f"Unsupported file type: {filename}", 400
            extension = filename.rsplit(".", 1)[-1].lower()
            if extension in ("txt", "md", "py", "csv"):
                file_text = uploaded.read().decode("utf-8", errors="replace")
            elif extension == "pdf":
                reader = PdfReader(BytesIO(uploaded.read()))
                file_text = "\n".join(page.extract_text() or "" for page in reader.pages)
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

        try:
            # Initialize the client the standard way
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
            )

            # Use the proper chat completions endpoint
            response = client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": f"""
            Create exactly 15 multiple-choice questions based on ALL uploaded documents.
            Return ONLY valid JSON. Use exactly this structure:

            {{
              "questions": [
                {{
                  "question": "Question text",
                  "options": {{
                    "A": "Option A",
                    "B": "Option B",
                    "C": "Option C",
                    "D": "Option D"
                  }},
                  "answer": "A",
                  "explanation": "Short explanation"
                }}
              ]
            }}

            Rules:
            - Exactly 15 questions.
            - Every question must have exactly 4 options.
            - The answer must be exactly one of: A, B, C, D.
            - Explanations should be short and student-friendly.
            - Questions must be based only on the uploaded documents.
            - Cover all uploaded documents as much as possible.
            - Do not include Markdown.
            - Do not include ```json.
            - Return ONLY the JSON object.

            Uploaded files:
            {", ".join(filenames)}

            Documents:
            {"".join(document_parts)}
            """
                    }
                ]
            )

            raw_answer = response.choices[0].message.content

            if not raw_answer:
                return "Model returned an empty response.", 500

            # Strip markdown fences
            raw_answer = raw_answer.strip()
            if raw_answer.startswith("```"):
                raw_answer = raw_answer.replace("```json", "", 1)
                raw_answer = raw_answer.replace("```", "")
                raw_answer = raw_answer.strip()

            quiz = json.loads(raw_answer)

            # Basic validation
            if "questions" not in quiz:
                raise ValueError("Invalid quiz format.")

            for question in quiz["questions"]:
                if not all(key in question for key in ("question", "options", "answer", "explanation")):
                    raise ValueError("One or more questions have missing fields.")
                if set(question["options"].keys()) != {"A", "B", "C", "D"}:
                    raise ValueError("Every question must have A, B, C and D options.")
                if question["answer"] not in {"A", "B", "C", "D"}:
                    raise ValueError("Invalid correct answer.")

        except json.JSONDecodeError as error:
            return f"Model did not return valid JSON: {error}", 500
        except Exception as error:
            return f"Quiz generation failed: {error}", 500

    return render_template("index.html", quiz=quiz)


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5001)
