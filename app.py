from __future__ import annotations

import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "online_learning_portal.db"
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__, static_folder="assets", static_url_path="/assets")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-production")


def db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql: str, params: tuple = (), one: bool = False, commit: bool = False):
    conn = db()
    cursor = conn.cursor()
    sql = sql.replace("%s", "?")
    cursor.execute(sql, params)
    if commit:
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return last_id
    rows = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows[0] if one and rows else (None if one else rows)


def init_database():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('admin', 'student')),
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            thumbnail TEXT,
            video_link TEXT,
            pdf_link TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, course_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()
    seed_sample_data()
    ensure_admin_exists()


def seed_sample_data():
    if query("SELECT COUNT(*) AS total FROM courses", one=True)["total"]:
        return
    php_course_id = query(
        "INSERT INTO courses (title, description, category, video_link, pdf_link) VALUES (?, ?, ?, ?, ?)",
        (
            "Python Flask Fundamentals",
            "Learn routing, templates, sessions, forms, and database access using Flask.",
            "Web Development",
            "https://www.youtube.com/embed/Z1RJmh_OqeA",
            "https://flask.palletsprojects.com/",
        ),
        commit=True,
    )
    bootstrap_course_id = query(
        "INSERT INTO courses (title, description, category, video_link, pdf_link) VALUES (?, ?, ?, ?, ?)",
        (
            "Bootstrap Responsive Design",
            "Build modern responsive layouts with Bootstrap grid, components, and dashboard UI patterns.",
            "Frontend",
            "https://www.youtube.com/embed/-qfEOE4vtxE",
            "https://getbootstrap.com/docs/5.3/getting-started/introduction/",
        ),
        commit=True,
    )
    query(
        "INSERT INTO quiz_questions (course_id, question, option_a, option_b, option_c, option_d, correct_answer) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (php_course_id, "Which Python framework is used in this project?", "Django", "Flask", "Laravel", "Spring", "B"),
        commit=True,
    )
    query(
        "INSERT INTO quiz_questions (course_id, question, option_a, option_b, option_c, option_d, correct_answer) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (bootstrap_course_id, "Which Bootstrap class creates a responsive row?", "container", "row", "btn", "alert", "B"),
        commit=True,
    )


def ensure_admin_exists():
    admin = query("SELECT id FROM users WHERE email=%s LIMIT 1", ("admin@portal.com",), one=True)
    if not admin:
        query(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            ("Portal Admin", "admin@portal.com", generate_password_hash("admin123"), "admin"),
            commit=True,
        )


def login_required(role: str | None = None):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapper

    return decorator


def current_user():
    if "user_id" not in session:
        return None
    return query(
        "SELECT id, name, email, role, phone, created_at FROM users WHERE id=%s",
        (session["user_id"],),
        one=True,
    )


def save_thumbnail(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    extension = file_storage.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_IMAGES:
        return None
    UPLOAD_DIR.mkdir(exist_ok=True)
    filename = f"course_{secrets.token_hex(8)}_{secure_filename(file_storage.filename)}"
    file_storage.save(UPLOAD_DIR / filename)
    return filename


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            flash("Please enter valid details. Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        try:
            query(
                "INSERT INTO users (name, email, phone, password, role) VALUES (%s, %s, %s, %s, %s)",
                (name, email, phone, generate_password_hash(password), "student"),
                commit=True,
            )
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_admin_exists()
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE email=%s LIMIT 1", (email,), one=True)

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "student_dashboard"))
        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():
    stats = {
        "students": query("SELECT COUNT(*) AS total FROM users WHERE role='student'", one=True)["total"],
        "courses": query("SELECT COUNT(*) AS total FROM courses", one=True)["total"],
        "enrollments": query("SELECT COUNT(*) AS total FROM enrollments", one=True)["total"],
    }
    recent = query(
        """
        SELECT e.enrolled_at, u.name, c.title
        FROM enrollments e
        JOIN users u ON u.id=e.user_id
        JOIN courses c ON c.id=e.course_id
        ORDER BY e.enrolled_at DESC LIMIT 8
        """
    )
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


@app.route("/admin/courses")
@login_required("admin")
def admin_courses():
    courses = query("SELECT * FROM courses ORDER BY created_at DESC")
    return render_template("admin/courses.html", courses=courses)


@app.route("/admin/course/add", methods=["GET", "POST"])
@app.route("/admin/course/<int:course_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def admin_course_form(course_id: int | None = None):
    course = None
    if course_id:
        course = query("SELECT * FROM courses WHERE id=%s", (course_id,), one=True)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        video_link = request.form.get("video_link", "").strip()
        pdf_link = request.form.get("pdf_link", "").strip()
        thumbnail = save_thumbnail(request.files.get("thumbnail")) or (course["thumbnail"] if course else None)

        if course_id:
            query(
                "UPDATE courses SET title=%s, description=%s, category=%s, thumbnail=%s, video_link=%s, pdf_link=%s WHERE id=%s",
                (title, description, category, thumbnail, video_link, pdf_link, course_id),
                commit=True,
            )
            flash("Course updated successfully.", "success")
        else:
            query(
                "INSERT INTO courses (title, description, category, thumbnail, video_link, pdf_link) VALUES (%s, %s, %s, %s, %s, %s)",
                (title, description, category, thumbnail, video_link, pdf_link),
                commit=True,
            )
            flash("Course added successfully.", "success")
        return redirect(url_for("admin_courses"))
    return render_template("admin/course_form.html", course=course)


@app.route("/admin/course/<int:course_id>/delete")
@login_required("admin")
def admin_course_delete(course_id):
    query("DELETE FROM courses WHERE id=%s", (course_id,), commit=True)
    flash("Course deleted successfully.", "success")
    return redirect(url_for("admin_courses"))


@app.route("/admin/students")
@login_required("admin")
def admin_students():
    students = query(
        """
        SELECT u.*, COUNT(e.id) AS enrollments
        FROM users u
        LEFT JOIN enrollments e ON e.user_id=u.id
        WHERE u.role='student'
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    )
    return render_template("admin/students.html", students=students)


@app.route("/admin/enrollments")
@login_required("admin")
def admin_enrollments():
    enrollments = query(
        """
        SELECT e.enrolled_at, u.name, u.email, c.title
        FROM enrollments e
        JOIN users u ON u.id=e.user_id
        JOIN courses c ON c.id=e.course_id
        ORDER BY e.enrolled_at DESC
        """
    )
    return render_template("admin/enrollments.html", enrollments=enrollments)


@app.route("/admin/quiz")
@login_required("admin")
def admin_quiz():
    questions = query(
        "SELECT q.*, c.title FROM quiz_questions q JOIN courses c ON c.id=q.course_id ORDER BY q.created_at DESC"
    )
    return render_template("admin/quiz.html", questions=questions)


@app.route("/admin/quiz/add", methods=["GET", "POST"])
@app.route("/admin/quiz/<int:question_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def admin_quiz_form(question_id: int | None = None):
    courses = query("SELECT id, title FROM courses ORDER BY title")
    question = query("SELECT * FROM quiz_questions WHERE id=%s", (question_id,), one=True) if question_id else None
    if request.method == "POST":
        data = (
            request.form.get("course_id"),
            request.form.get("question", "").strip(),
            request.form.get("option_a", "").strip(),
            request.form.get("option_b", "").strip(),
            request.form.get("option_c", "").strip(),
            request.form.get("option_d", "").strip(),
            request.form.get("correct_answer", "A"),
        )
        if question_id:
            query(
                "UPDATE quiz_questions SET course_id=%s, question=%s, option_a=%s, option_b=%s, option_c=%s, option_d=%s, correct_answer=%s WHERE id=%s",
                (*data, question_id),
                commit=True,
            )
            flash("Quiz question updated.", "success")
        else:
            query(
                "INSERT INTO quiz_questions (course_id, question, option_a, option_b, option_c, option_d, correct_answer) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                data,
                commit=True,
            )
            flash("Quiz question added.", "success")
        return redirect(url_for("admin_quiz"))
    return render_template("admin/quiz_form.html", courses=courses, question=question)


@app.route("/admin/quiz/<int:question_id>/delete")
@login_required("admin")
def admin_quiz_delete(question_id):
    query("DELETE FROM quiz_questions WHERE id=%s", (question_id,), commit=True)
    flash("Quiz question deleted.", "success")
    return redirect(url_for("admin_quiz"))


@app.route("/student/dashboard")
@login_required("student")
def student_dashboard():
    user_id = session["user_id"]
    stats = {
        "courses": query("SELECT COUNT(*) AS total FROM courses", one=True)["total"],
        "my_courses": query("SELECT COUNT(*) AS total FROM enrollments WHERE user_id=%s", (user_id,), one=True)["total"],
        "certificates": query(
            "SELECT COUNT(DISTINCT course_id) AS total FROM results WHERE user_id=%s AND percentage>=60",
            (user_id,),
            one=True,
        )["total"],
    }
    results = query(
        """
        SELECT r.*, c.title
        FROM results r
        JOIN courses c ON c.id=r.course_id
        WHERE r.user_id=%s
        ORDER BY r.completed_at DESC LIMIT 6
        """,
        (user_id,),
    )
    return render_template("student/dashboard.html", stats=stats, results=results)


@app.route("/student/profile")
@login_required("student")
def student_profile():
    return render_template("student/profile.html")


@app.route("/student/courses")
@login_required("student")
def student_courses():
    courses = query(
        """
        SELECT c.*, e.id AS enrollment_id
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id=c.id AND e.user_id=%s
        ORDER BY c.created_at DESC
        """,
        (session["user_id"],),
    )
    return render_template("student/courses.html", courses=courses)


@app.route("/student/enroll/<int:course_id>")
@login_required("student")
def student_enroll(course_id):
    try:
        query(
            "INSERT INTO enrollments (user_id, course_id) VALUES (%s, %s)",
            (session["user_id"], course_id),
            commit=True,
        )
        flash("Enrollment successful.", "success")
    except sqlite3.IntegrityError:
        flash("You are already enrolled in this course.", "warning")
    return redirect(url_for("student_courses"))


@app.route("/student/my-courses")
@login_required("student")
def student_my_courses():
    courses = query(
        """
        SELECT c.*, e.enrolled_at,
          (SELECT percentage FROM results r WHERE r.user_id=%s AND r.course_id=c.id ORDER BY completed_at DESC LIMIT 1) AS latest_percentage
        FROM enrollments e
        JOIN courses c ON c.id=e.course_id
        WHERE e.user_id=%s
        ORDER BY e.enrolled_at DESC
        """,
        (session["user_id"], session["user_id"]),
    )
    return render_template("student/my_courses.html", courses=courses)


@app.route("/student/quiz/<int:course_id>", methods=["GET", "POST"])
@login_required("student")
def student_quiz(course_id):
    enrolled = query(
        "SELECT c.* FROM courses c JOIN enrollments e ON e.course_id=c.id WHERE c.id=%s AND e.user_id=%s",
        (course_id, session["user_id"]),
        one=True,
    )
    if not enrolled:
        flash("Please enroll before attempting the quiz.", "danger")
        return redirect(url_for("student_my_courses"))

    questions = query("SELECT * FROM quiz_questions WHERE course_id=%s ORDER BY id", (course_id,))
    if request.method == "POST":
        score = sum(1 for q in questions if request.form.get(f"answer_{q['id']}") == q["correct_answer"])
        total = len(questions)
        percentage = round((score / total) * 100, 2) if total else 0
        query(
            "INSERT INTO results (user_id, course_id, score, total_questions, percentage) VALUES (%s, %s, %s, %s, %s)",
            (session["user_id"], course_id, score, total, percentage),
            commit=True,
        )
        return redirect(url_for("student_result", course_id=course_id))
    return render_template("student/quiz.html", course=enrolled, questions=questions)


@app.route("/student/result/<int:course_id>")
@login_required("student")
def student_result(course_id):
    result = query(
        """
        SELECT r.*, c.title
        FROM results r
        JOIN courses c ON c.id=r.course_id
        WHERE r.user_id=%s AND r.course_id=%s
        ORDER BY r.completed_at DESC LIMIT 1
        """,
        (session["user_id"], course_id),
        one=True,
    )
    if not result:
        flash("No result found for this course.", "danger")
        return redirect(url_for("student_my_courses"))
    return render_template("student/result.html", result=result)


@app.route("/student/certificate/<int:course_id>")
@login_required("student")
def student_certificate(course_id):
    certificate = query(
        """
        SELECT r.*, c.title, u.name
        FROM results r
        JOIN courses c ON c.id=r.course_id
        JOIN users u ON u.id=r.user_id
        WHERE r.user_id=%s AND r.course_id=%s AND r.percentage>=60
        ORDER BY r.completed_at DESC LIMIT 1
        """,
        (session["user_id"], course_id),
        one=True,
    )
    if not certificate:
        flash("Certificate is available only after scoring at least 60%.", "danger")
        return redirect(url_for("student_my_courses"))
    return render_template("student/certificate.html", certificate=certificate)


init_database()


if __name__ == "__main__":
    app.run(debug=True)
