import os
import openai
from flask import Flask, redirect, render_template, request, url_for, session, jsonify, abort
import re
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
import sqlite3
import json
from oauthlib.oauth2 import WebApplicationClient
import requests


from db import init_db_command
from user import User
app = Flask(__name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)

# Naive database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
# Flask-Login helper to retrieve a user from our db


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/")
def index():
    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))
    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400
    # Create a user in your db with the information provided
    # by Google
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("input", name= "yash"))


@app.route("/input", methods=["GET", "POST"])
@login_required
def input():
    if request.method == "POST":
        title = request.form["animal"]
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_list_title(title),
            temperature=0.5,
            max_tokens=2048,
            top_p=1
        )
        li = response.choices[0].text.strip().split("\n")
        result = [re.sub(r'^\d+\.', '', item).strip() for item in li]
        print(result)
        return render_template("input.html", results=result ,current_user = current_user)

    return render_template("input.html", results=None,current_user = current_user)
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/content/<slide_title>", methods=["GET"])
@login_required
def content(slide_title):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=generate_contnet(slide_title),
        temperature=0.5,
        max_tokens=2048,
        top_p=1
    )
    result = response.choices[0].text.strip()
    print(result)
    return render_template("content.html", content=result)


def generate_prompt(title):
    return f""" generate the ppt content slide by slide with titles on the topic {title} in json type with slide  number as key and slide data as value of that key"""


def generate_title(title):
    return f"""provide me a list of presentation slides on the topic {title}. Each slide should include a slide_{{number}} as the key, a title, and the data as the values. it have 8 slides must be in JSON format"""


def generate_list_title(title):
    return f"""generate just titles of slides presentation on the topic {title} it has 8 slides,"""


def generate_contnet(slide_title):
    return f"""generate the paragraph on the topic {slide_title})"""


if __name__ == "__main__":
    app.run(debug=True)
