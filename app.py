from flask import Flask, render_template
from openai import OpenAI
from waitress import serve

app = Flask(__name__)

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)

MODEL = "prism-ml/bonsai-27b"


@app.route("/")
def index():
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise, helpful assistant.",
                },
                {
                    "role": "user",
                    "content": "Explain what a Python decorator is.",
                },
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as error:
        return f"LM Studio error: {error}", 500


@app.route("/hello")
def hello():
    return render_template("hello.html")


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5001)
