from flask import Flask, render_template, request, redirect, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

import time
import random
import os
import base64
import cv2
import numpy as np


app = Flask(__name__)


# =========================================================
# SESSION CONFIG
# =========================================================

app.secret_key = os.getenv(
    "SECRET_KEY",
    "super_secret_key_123"
)

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False


# =========================================================
# DATABASE CONFIG
# =========================================================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///driving_data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# DATABASE MODELS
# =========================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(100),
        nullable=False
    )


class Application(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_email = db.Column(
        db.String(100),
        nullable=False
    )

    fullname = db.Column(
        db.String(100)
    )

    age = db.Column(
        db.String(10)
    )

    aadhar = db.Column(
        db.String(20)
    )

    vehicle = db.Column(
        db.String(20)
    )


class Result(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_email = db.Column(
        db.String(100)
    )

    theory = db.Column(
        db.Integer
    )

    simulator = db.Column(
        db.Integer
    )

    total = db.Column(
        db.Integer
    )


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

with app.app_context():

    db.create_all()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "welcome.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if not email or not password:

            return (
                "Email and password are required ❌"
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            return (
                "Email already exists ❌"
            )

        new_user = User(
            email=email,
            password=password
        )

        db.session.add(
            new_user
        )

        db.session.commit()

        return redirect(
            "/login"
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if not email or not password:

            return (
                "Email and password are required ❌"
            )

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            return (
                "Invalid email or password ❌"
            )

        if user.password != password:

            return (
                "Invalid email or password ❌"
            )

        session.clear()

        session["user"] = user.email

        return redirect(
            "/dashboard"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:

        return redirect(
            "/login"
        )

    return render_template(
        "dashboard.html"
    )


# =========================================================
# APPLICATION
# =========================================================

@app.route(
    "/application",
    methods=["GET", "POST"]
)
def application():

    if "user" not in session:

        return redirect(
            "/login"
        )

    if request.method == "POST":

        vehicle = request.form.get(
            "vehicle"
        )

        data = Application(

            user_email=session["user"],

            fullname=request.form.get(
                "fullname"
            ),

            age=request.form.get(
                "age"
            ),

            aadhar=request.form.get(
                "aadhar"
            ),

            vehicle=vehicle
        )

        db.session.add(
            data
        )

        db.session.commit()

        session["vehicle"] = vehicle

        return redirect(
            "/face"
        )

    return render_template(
        "application.html"
    )


# =========================================================
# FACE PAGE
# =========================================================

@app.route("/face")
def face():

    if "user" not in session:

        return redirect(
            "/login"
        )

    return render_template(
        "verify.html"
    )


# =========================================================
# UPLOAD PASSPORT
# =========================================================

@app.route(
    "/upload_passport",
    methods=["POST"]
)
def upload_passport():

    if "user" not in session:

        return jsonify({
            "status":
                "❌ Please login first"
        }), 401

    file = request.files.get(
        "file"
    )

    if not file:

        return jsonify({
            "status":
                "❌ No file selected"
        })

    if file.filename == "":

        return jsonify({
            "status":
                "❌ Invalid file"
        })

    try:

        os.makedirs(
            "static/faces",
            exist_ok=True
        )

        safe_email = (
            session["user"]
            .replace("@", "_")
            .replace(".", "_")
        )

        filename = (
            f"passport_{safe_email}.jpg"
        )

        path = os.path.join(
            "static",
            "faces",
            filename
        )

        file.save(
            path
        )

        session["passport"] = path

        print(
            "\n========== PASSPORT UPLOAD =========="
        )

        print(
            "Passport saved:",
            path
        )

        print(
            "=====================================\n"
        )

        return jsonify({
            "status":
                "✅ Passport uploaded"
        })

    except Exception as e:

        print(
            "PASSPORT UPLOAD ERROR:"
        )

        print(
            str(e)
        )

        return jsonify({

            "status":
                "❌ Passport upload failed",

            "error":
                str(e)

        }), 500


# =========================================================
# FACE VERIFICATION
# =========================================================

@app.route(
    "/verify_face",
    methods=["POST"]
)
def verify_face():

    print(
        "\n========== VERIFY FACE REQUEST =========="
    )

    try:

        # -------------------------------------------------
        # LOGIN CHECK
        # -------------------------------------------------

        if "user" not in session:

            return jsonify({

                "status":
                    "❌ Please login first"

            }), 401


        # -------------------------------------------------
        # PASSPORT CHECK
        # -------------------------------------------------

        passport_path = session.get(
            "passport"
        )

        print(
            "Passport:",
            passport_path
        )

        if not passport_path:

            return jsonify({

                "status":
                    "❌ Please upload passport photo first"

            })

        if not os.path.exists(
            passport_path
        ):

            return jsonify({

                "status":
                    "❌ Passport photo not found"

            })


        # -------------------------------------------------
        # CAMERA DATA
        # -------------------------------------------------

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({

                "status":
                    "❌ No camera image received"

            }), 400

        image_data = data.get(
            "image"
        )

        if not image_data:

            return jsonify({

                "status":
                    "❌ No camera image received"

            }), 400

        print(
            "Camera image received"
        )


        # -------------------------------------------------
        # REMOVE BASE64 HEADER
        # -------------------------------------------------

        if "," in image_data:

            image_data = image_data.split(
                ",",
                1
            )[1]


        # -------------------------------------------------
        # DECODE IMAGE
        # -------------------------------------------------

        try:

            image_bytes = base64.b64decode(
                image_data
            )

        except Exception as e:

            print(
                "BASE64 ERROR:",
                e
            )

            return jsonify({

                "status":
                    "❌ Invalid camera image"

            }), 400


        # -------------------------------------------------
        # OPENCV
        # -------------------------------------------------

        np_arr = np.frombuffer(
            image_bytes,
            np.uint8
        )

        live_img = cv2.imdecode(
            np_arr,
            cv2.IMREAD_COLOR
        )

        if live_img is None:

            return jsonify({

                "status":
                    "❌ Invalid camera image"

            }), 400

        print(
            "Camera image decoded successfully"
        )


        # -------------------------------------------------
        # SAVE CAMERA IMAGE
        # -------------------------------------------------

        os.makedirs(
            "static/faces",
            exist_ok=True
        )

        safe_email = (
            session["user"]
            .replace("@", "_")
            .replace(".", "_")
        )

        live_path = os.path.join(

            "static",
            "faces",
            f"live_{safe_email}.jpg"

        )

        if not cv2.imwrite(
            live_path,
            live_img
        ):

            return jsonify({

                "status":
                    "❌ Could not save camera image"

            }), 500

        print(
            "Camera image saved:",
            live_path
        )


        # -------------------------------------------------
        # DEEPFACE
        # -------------------------------------------------

        print(
            "\nStarting DeepFace..."
        )

        # IMPORTANT:
        # DeepFace is imported only when
        # face verification is requested.
        from deepface import DeepFace


        result = DeepFace.verify(

            img1_path=passport_path,

            img2_path=live_path,

            model_name="Facenet",

            detector_backend="opencv",

            distance_metric="cosine",

            enforce_detection=True

        )


        print(
            "\nDEEPFACE RESULT:"
        )

        print(
            result
        )


        # -------------------------------------------------
        # CHECK RESULT
        # -------------------------------------------------

        distance = result.get(
            "distance"
        )

        verified = result.get(
            "verified",
            False
        )


        if verified:

            session["face_verified"] = True

            print(
                "✅ FACE MATCHED"
            )

            return jsonify({

                "status":
                    "✅ Face Matched",

                "confidence":
                    f"Distance: {distance:.4f}"

            })


        session["face_verified"] = False

        print(
            "❌ FACE NOT MATCHED"
        )

        return jsonify({

            "status":
                "❌ Face Not Matching",

            "confidence":
                f"Distance: {distance:.4f}"

        })


    except Exception as e:

        print(
            "\n========== FACE VERIFICATION ERROR =========="
        )

        print(
            "Type:",
            type(e).__name__
        )

        print(
            "Error:",
            str(e)
        )

        print(
            "=============================================\n"
        )

        session["face_verified"] = False

        return jsonify({

            "status":
                "❌ Face verification failed",

            "error":
                str(e)

        }), 500


# =========================================================
# FACE DONE
# =========================================================

@app.route("/face_done")
def face_done():

    if "user" not in session:

        return redirect(
            "/login"
        )

    if not session.get(
        "face_verified"
    ):

        return redirect(
            "/face"
        )

    return redirect(
        "/slot"
    )


# =========================================================
# SLOT
# =========================================================

@app.route("/slot")
def slot():

    if "user" not in session:

        return redirect(
            "/login"
        )

    if not session.get(
        "face_verified"
    ):

        return redirect(
            "/face"
        )

    return render_template(
        "slot.html"
    )


# =========================================================
# THEORY
# =========================================================

@app.route("/theory")
def theory():

    if "user" not in session:

        return redirect(
            "/login"
        )

    questions = [

        {
            "q":
                "Speed limit?",

            "options": [
                "40",
                "60",
                "80",
                "100"
            ],

            "ans":
                "60"
        },

        {
            "q":
                "Red signal?",

            "options": [
                "Go",
                "Stop",
                "Wait",
                "Slow"
            ],

            "ans":
                "Stop"
        },

        {
            "q":
                "Seat belt?",

            "options": [
                "Optional",
                "Safety",
                "None",
                "Fashion"
            ],

            "ans":
                "Safety"
        },

        {
            "q":
                "Helmet?",

            "options": [
                "Optional",
                "Mandatory",
                "None",
                "Fashion"
            ],

            "ans":
                "Mandatory"
        },

        {
            "q":
                "Overtake?",

            "options": [
                "Left",
                "Right",
                "Anywhere",
                "None"
            ],

            "ans":
                "Right"
        }

    ]

    return render_template(
        "theory.html",
        questions=questions
    )


# =========================================================
# SUBMIT THEORY
# =========================================================

@app.route(
    "/submit_theory",
    methods=["POST"]
)
def submit_theory():

    if "user" not in session:

        return jsonify({

            "status":
                "❌ Please login first"

        }), 401

    session["theory_done"] = True

    return jsonify({

        "status":
            "ok"

    })


# =========================================================
# SET MODE
# =========================================================

@app.route(
    "/set_mode",
    methods=["POST"]
)
def set_mode():

    if "user" not in session:

        return jsonify({

            "status":
                "❌ Please login first"

        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    session["mode"] = data.get(
        "mode",
        "bad"
    )

    return jsonify({

        "status":
            "ok"

    })


# =========================================================
# SIMULATOR
# =========================================================

@app.route("/simulator")
def simulator():

    if "user" not in session:

        return redirect(
            "/login"
        )

    if not session.get(
        "theory_done"
    ):

        return redirect(
            "/theory"
        )

    return render_template(
        "simulator.html"
    )


# =========================================================
# AI VIDEO CONFIGURATION
# =========================================================

UPLOAD_FOLDER = (
    "static/driving_videos"
)

ALLOWED_VIDEO_EXTENSIONS = {

    "mp4",
    "avi",
    "mov",
    "mkv"

}

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# VIDEO FILE CHECK
# =========================================================

def allowed_video(filename):

    return (

        "." in filename

        and

        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_VIDEO_EXTENSIONS

    )


# =========================================================
# RESULT
# =========================================================

@app.route("/result")
def result():

    if "user" not in session:

        return redirect(
            "/login"
        )

    mode = session.get(
        "mode",
        "bad"
    )


    if mode == "bad":

        theory_score = random.randint(
            30,
            50
        )

        sim_score = random.randint(
            20,
            45
        )

    else:

        theory_score = random.randint(
            80,
            95
        )

        sim_score = random.randint(
            75,
            90
        )


    total = (

        theory_score
        +
        sim_score

    ) // 2


    status = (

        "PASS"
        if total >= 60
        else "FAIL"

    )


    result_data = Result(

        user_email=session["user"],

        theory=theory_score,

        simulator=sim_score,

        total=total

    )


    db.session.add(
        result_data
    )

    db.session.commit()


    session["result_status"] = status


    return render_template(

        "result.html",

        theory=theory_score,

        sim=sim_score,

        total=total,

        status=status

    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/login"
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    os.makedirs(
        "static/faces",
        exist_ok=True
    )

    with app.app_context():

        db.create_all()

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=False,

        use_reloader=False

    )