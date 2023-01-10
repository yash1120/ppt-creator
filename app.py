import os
import openai
from flask import Flask, redirect, render_template, request, url_for
import json

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        title = request.form["animal"]
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_title(title),
            temperature=0.3,
            max_tokens=2048,
            top_p=1
        )
        print(response.choices[0].text.strip())

        return render_template("index.html", result=json.loads(response.choices[0].text.strip()))

    return render_template("index.html", result=None)


def generate_prompt(title):
    return f""" generate the ppt content slide by slide with titles on the topic {title} in json type with slide  number as key and slide data as value of that key"""

def generate_title(title):
    return f"""generate the ppt titles and content of slides having 8 slides on the topic {title} with "slide_{{number}}" as key and title and title data as value in json format""" 