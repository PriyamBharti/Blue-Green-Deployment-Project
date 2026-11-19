from flask import Flask, jsonify
import os

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "1.0")
APP_COLOR = os.getenv("APP_COLOR", "blue")


@app.route("/")
def home():
    return f"""
    <html>
        <head>
            <title>Blue-Green Deployment Demo</title>
        </head>
        <body style="font-family: Arial; text-align: center; margin-top: 100px;">
            <h1>Blue-Green Deployment Demo</h1>
            <h2>Currently Running: {APP_COLOR.upper()} Environment</h2>
            <h3>Application Version: {APP_VERSION}</h3>
            <p>Deployment successfully running on Kubernetes!</p>
        </body>
    </html>
    """


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": APP_VERSION,
        "environment": APP_COLOR
    })


@app.route("/version")
def version():
    return jsonify({
        "application": "Blue-Green Deployment Demo",
        "version": APP_VERSION,
        "environment": APP_COLOR
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)