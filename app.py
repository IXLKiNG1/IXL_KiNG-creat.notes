from flask import Flask, render_template, render_template_string, request, redirect, url_for
import sqlite3
import os
from datetime import datetime


# =========================================================
# إعدادات المشروع
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")


app_Not = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


# =========================================================
# الاتصال بقاعدة البيانات
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


# =========================================================
# إعدادات الصفحات
# =========================================================

def get_page_settings(page):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT background, background_color
        FROM page_settings
        WHERE page = ?
        """,
        (page,)
    )

    settings = cursor.fetchone()

    conn.close()

    return settings


# =========================================================
# إنشاء الجداول
# =========================================================

def create_table():

    conn = get_db()
    cursor = conn.cursor()

    # جدول المذكرات
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            note TEXT,
            type TEXT,
            created_at TEXT,
            updated_at TEXT,
            pinned INTEGER DEFAULT 0
        )
        """
    )

    # جدول إعدادات الصفحات
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT UNIQUE,
            background TEXT DEFAULT 'default',
            background_color TEXT DEFAULT '#ffffff'
        )
        """
    )

    # إعداد افتراضي لكل صفحة
    cursor.execute(
        """
        INSERT OR IGNORE INTO page_settings
        (page, background, background_color)
        VALUES
        ('index', 'default', '#ffffff'),
        ('note', 'default', '#ffffff'),
        ('edit', 'default', '#ffffff')
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# عرض index.html الموجود بجانب app.py
# =========================================================

def render_index(**context):

    index_path = os.path.join(BASE_DIR, "index.html")

    try:
        with open(index_path, "r", encoding="utf-8") as file:
            index_html = file.read()

    except FileNotFoundError:
        return "خطأ: لم يتم العثور على index.html", 500

    return render_template_string(
        index_html,
        **context
    )


# =========================================================
# الصفحة الرئيسية
# =========================================================

@app_Not.route("/")
def index_page():
    return home_page()


@app_Not.route("/home")
def home_page():

    search_text = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    if search_text:

        cursor.execute(
            """
            SELECT *
            FROM notes
            WHERE title LIKE ? OR note LIKE ?
            ORDER BY pinned DESC, id DESC
            """,
            (
                f"%{search_text}%",
                f"%{search_text}%"
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM notes
            ORDER BY pinned DESC, id DESC
            """
        )

    notes = cursor.fetchall()

    preview_notes = []

    for note in notes:

        note_id = note[0]
        title = note[1]
        content = note[2].split("\n")[0]

        preview_notes.append(
            (
                note_id,
                title,
                content,
                note[3],   # type
                note[6],   # pinned
                note[4],   # created_at
                note[5]    # updated_at
            )
        )

    conn.close()

    settings = get_page_settings("index")

    return render_index(
        con=preview_notes,
        settings=settings,
        error=None
    )


# =========================================================
# حفظ مذكرة جديدة
# =========================================================

@app_Not.route("/save", methods=["POST"])
def Saving_page():

    title = request.form.get("top", "")
    note = request.form.get("int", "")
    note_type = request.form.get("note_type", "temporary")

    # يجب كتابة شيء واحد على الأقل
    if not title.strip() and not note.strip():

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM notes
            ORDER BY pinned DESC, id DESC
            """
        )

        notes = cursor.fetchall()

        preview_notes = []

        for old_note in notes:

            note_id = old_note[0]
            old_title = old_note[1]
            content = old_note[2].split("\n")[0]

            preview_notes.append(
                (
                    note_id,
                    old_title,
                    content,
                    old_note[3],
                    old_note[6],
                    old_note[4],
                    old_note[5]
                )
            )

        conn.close()

        settings = get_page_settings("index")

        return render_index(
            con=preview_notes,
            settings=settings,
            error="⚠️ اكتب شيئًا في العنوان أو المحتوى على الأقل"
        )

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO notes
        (title, note, type, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            title,
            note,
            note_type,
            current_time,
            current_time
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index_page"))


# =========================================================
# فتح المذكرة
# =========================================================

@app_Not.route("/note/<int:note_id>")
def note_page(note_id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM notes
        WHERE id = ?
        """,
        (note_id,)
    )

    note = cursor.fetchone()

    conn.close()

    if note is None:
        return "المذكرة غير موجودة", 404

    settings = get_page_settings("note")

    return render_template(
        "note.html",
        note=note,
        settings=settings
    )


# =========================================================
# تثبيت / إلغاء تثبيت المذكرة
# =========================================================

@app_Not.route("/toggle_pin", methods=["POST"])
def toggle_pin():

    note_id = int(request.form["id"])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notes
        SET pinned = CASE
            WHEN pinned = 0 THEN 1
            ELSE 0
        END
        WHERE id = ?
        """,
        (note_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("note_page", note_id=note_id))


# =========================================================
# حذف المذكرة
# =========================================================

@app_Not.route("/delete", methods=["POST"])
def delete_page():

    note_id = int(request.form["id"])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM notes
        WHERE id = ?
        """,
        (note_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index_page"))


# =========================================================
# صفحة تعديل المذكرة
# =========================================================

@app_Not.route("/edit", methods=["POST"])
def edit_page():

    note_id = int(request.form["id"])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM notes
        WHERE id = ?
        """,
        (note_id,)
    )

    note = cursor.fetchone()

    conn.close()

    if note is None:
        return "المذكرة غير موجودة", 404

    settings = get_page_settings("edit")

    return render_template(
        "edit.html",
        note=note,
        settings=settings
    )


# =========================================================
# حفظ تعديل المذكرة
# =========================================================

@app_Not.route("/save_edit", methods=["POST"])
def save_edit_page():

    note_id = request.form.get("id")
    title = request.form.get("top", "")
    note = request.form.get("int", "")
    note_type = request.form.get("note_type", "temporary")

    if not note_id:
        return "خطأ: لم يتم إرسال ID المذكرة", 400

    if not title.strip() and not note.strip():
        return "⚠️ يجب كتابة شيء في العنوان أو المحتوى", 400

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notes
        SET title = ?,
            note = ?,
            type = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            title,
            note,
            note_type,
            updated_at,
            int(note_id)
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index_page"))


# =========================================================
# إعدادات الصفحة الرئيسية
# =========================================================

@app_Not.route("/settings/index")
def settings_index():

    settings = get_page_settings("index")

    return render_template(
        "settings_index.html",
        settings=settings
    )


@app_Not.route("/save_settings/index", methods=["POST"])
def save_settings_index():

    background = request.form.get(
        "background",
        "default"
    )

    background_color = request.form.get(
        "background_color",
        "#ffffff"
    )

    image = request.files.get("custom_background")

    # إذا اختار المستخدم صورة من جهازه
    if image and image.filename:

        os.makedirs(
            UPLOADS_DIR,
            exist_ok=True
        )

        # اسم الملف فقط
        filename = os.path.basename(image.filename)

        image_path = os.path.join(
            UPLOADS_DIR,
            filename
        )

        image.save(image_path)

        # المسار بالنسبة إلى static
        background = "uploads/" + filename

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE page_settings
        SET background = ?,
            background_color = ?
        WHERE page = 'index'
        """,
        (
            background,
            background_color
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("settings_index"))


# =========================================================
# إعدادات صفحة المذكرة
# =========================================================

@app_Not.route("/settings/note")
def settings_note():

    settings = get_page_settings("note")

    return render_template(
        "settings_note.html",
        settings=settings
    )


@app_Not.route("/save_settings/note", methods=["POST"])
def save_settings_note():

    background = request.form.get(
        "background",
        "default"
    )

    background_color = request.form.get(
        "background_color",
        "#ffffff"
    )

    # توحيد أسماء الخلفيات القديمة
    background_map = {
        "BG1": "img/BG1 app_Not.jpg",
        "BG6": "img/BG6 app_Not.jpg"
    }

    background = background_map.get(
        background,
        background
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE page_settings
        SET background = ?,
            background_color = ?
        WHERE page = 'note'
        """,
        (
            background,
            background_color
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("settings_note"))


# =========================================================
# إعدادات صفحة التعديل
# =========================================================

@app_Not.route("/settings/edit")
def settings_edit():

    settings = get_page_settings("edit")

    return render_template(
        "settings_edit.html",
        settings=settings
    )


@app_Not.route("/save_settings/edit", methods=["POST"])
def save_settings_edit():

    background = request.form.get(
        "background",
        "default"
    )

    background_color = request.form.get(
        "background_color",
        "#ffffff"
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE page_settings
        SET background = ?,
            background_color = ?
        WHERE page = 'edit'
        """,
        (
            background,
            background_color
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("settings_edit"))


# =========================================================
# تشغيل المشروع
# =========================================================

create_table()


if __name__ == "__main__":
    app_Not.run()