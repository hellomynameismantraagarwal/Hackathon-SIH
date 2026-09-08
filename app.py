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


# LM Studio local server endpoint (default port is 1234)
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

def encode_image_to_base64(file_storage):
    """Converts a Flask FileStorage object directly to a base64 string."""
    return base64.b64encode(file_storage.read()).decode('utf-8')

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    # 1. Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # 2. Convert the image file to base64 for LM Studio's Vision API
        base64_image = encode_image_to_base64(file)

        # 3. Get an optional prompt from the form data
        prompt = request.form.get('prompt', 'What is in this image?')

        # 4. Prepare the payload matching LM Studio / OpenAI Vision format
        payload = {
            "model": "meta-llama-3.1-8b-instruct", # Change to your loaded vision model
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.2
        }

        # 5. Forward the request to LM Studio
        response = requests.post(LM_STUDIO_URL, json=payload)

        # 6. Return LM Studio's response back to the client
        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": str(efixed)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
