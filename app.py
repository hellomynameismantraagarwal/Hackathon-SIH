from flask import *
import waitress


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/hello')
def hello():
    return render_template('hello.html')
waitress.serve(app, host='0.0.0.0',port=5000)
