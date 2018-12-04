from flask import Flask
app = Flask(__name__)
app.run(host='0.0.0.0', port=5000, debug=False)

@app.route("/")
def hello():
    return "Hello World!"