from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename


# =========================================================
# المسار الأساسي للمشروع
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =========================================================
# إنشاء تطبيق Flask
#
# index.html موجود بجانب app.py
# وباقي الصفحات موجودة داخل templates
# =========================================================

app_Not = Flask(
    __name__,
    template_folder=BASE_DIR
)


# =========================================================
# قاعدة البيانات
# =========================================================

def get_db():

    db_path = os.path.join(
        BASE_DIR,
        "database.db"
    )

    conn = sqlite3.connect(db_path)

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

    # إعدادات افتراضية
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
# دالة تجهيز المذكرات للعرض
# =========================================================

def get_preview_notes(search_text=""):

    conn = get_db()
    cursor = conn.cursor()

    if search_text:

        cursor.execute(
            """
            SELECT *
            FROM notes

            WHERE title LIKE ?
            OR note LIKE ?

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

        # أول سطر فقط للمعاينة
        content = note[2].split("\n")[0]

        note_type = note[3]

        created_at = note[4]

        updated_at = note[5]

        pinned = note[6]

        preview_notes.append(
            (
                note_id,
                title,
                content,
                note_type,
                pinned,
                created_at,
                updated_at
            )
        )

    conn.close()

    return preview_notes


# =========================================================
# الصفحة الرئيسية
#
# index.html موجود بجانب app.py
# =========================================================

@app_Not.route("/")
@app_Not.route("/home")
def home_page():

    search_text = request.args.get(
        "search",
        ""
    )

    notes = get_preview_notes(
        search_text
    )

    settings = get_page_settings(
        "index"
    )

    return render_template(
        "index.html",
        con=notes,
        settings=settings
    )


# =========================================================
# حفظ مذكرة جديدة
# =========================================================

@app_Not.route(
    "/save",
    methods=["POST"]
)
def Saving_page():

    title = request.form.get(
        "top",
        ""
    )

    note = request.form.get(
        "int",
        ""
    )

    note_type = request.form.get(
        "note_type",
        "temporary"
    )

    # التأكد من وجود شيء مكتوب
    if not title.strip() and not note.strip():

        notes = get_preview_notes()

        settings = get_page_settings(
            "index"
        )

        return render_template(
            "index.html",
            con=notes,
            settings=settings,
            error="⚠️ اكتب شيئًا في العنوان أو المحتوى على الأقل"
        )

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO notes
        (
            title,
            note,
            type,
            created_at,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?)
        """,

        (
            title,
            note,
            note_type,
            now,
            now
        )
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("home_page")
    )


# =========================================================
# فتح المذكرة
# =========================================================

@app_Not.route(
    "/note/<int:note_id>"
)
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

    settings = get_page_settings(
        "note"
    )

    return render_template(
        "templates/note.html",
        note=note,
        settings=settings
    )


# =========================================================
# حذف مذكرة
# =========================================================

@app_Not.route(
    "/delete",
    methods=["POST"]
)
def delete_page():

    note_id = request.form.get(
        "id"
    )

    if not note_id:

        return "معرف المذكرة غير موجود", 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM notes
        WHERE id = ?
        """,

        (int(note_id),)
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("home_page")
    )


# =========================================================
# تثبيت / إلغاء تثبيت
# =========================================================

@app_Not.route(
    "/toggle_pin",
    methods=["POST"]
)
def toggle_pin():

    note_id = request.form.get(
        "id"
    )

    if not note_id:

        return "معرف المذكرة غير موجود", 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notes

        SET pinned =
            CASE

                WHEN pinned = 0
                THEN 1

                ELSE 0

            END

        WHERE id = ?
        """,

        (int(note_id),)
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for(
            "note_page",
            note_id=int(note_id)
        )
    )


# =========================================================
# فتح صفحة التعديل
# =========================================================

@app_Not.route(
    "/edit",
    methods=["POST"]
)
def edit_page():

    note_id = request.form.get(
        "id"
    )

    if not note_id:

        return "معرف المذكرة غير موجود", 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM notes

        WHERE id = ?
        """,

        (int(note_id),)
    )

    note = cursor.fetchone()

    conn.close()

    if note is None:

        return "المذكرة غير موجودة", 404

    settings = get_page_settings(
        "edit"
    )

    return render_template(
        "templates/edit.html",
        note=note,
        settings=settings
    )


# =========================================================
# حفظ تعديل المذكرة
# =========================================================

@app_Not.route(
    "/save_edit",
    methods=["POST"]
)
def save_edit_page():

    note_id = request.form.get(
        "id"
    )

    title = request.form.get(
        "top",
        ""
    )

    note = request.form.get(
        "int",
        ""
    )

    note_type = request.form.get(
        "note_type",
        "temporary"
    )

    if not note_id:

        return "خطأ: لم يتم إرسال ID المذكرة", 400

    if not title.strip() and not note.strip():

        return (
            "⚠️ يجب كتابة شيء في العنوان أو المحتوى",
            400
        )

    updated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE notes

        SET
            title = ?,
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

    return redirect(
        url_for("home_page")
    )


# =========================================================
# إعدادات الصفحة الرئيسية
# =========================================================

@app_Not.route(
    "/settings/index"
)
def settings_index():

    settings = get_page_settings(
        "index"
    )

    return render_template(
        "templates/settings_index.html",
        settings=settings
    )


# =========================================================
# حفظ إعدادات الصفحة الرئيسية
# =========================================================

@app_Not.route(
    "/save_settings/index",
    methods=["POST"]
)
def save_settings_index():

    background = request.form.get(
        "background",
        "default"
    )

    background_color = request.form.get(
        "background_color",
        "#ffffff"
    )

    image = request.files.get(
        "custom_background"
    )

    # رفع صورة من الجهاز
    if image and image.filename:

        filename = secure_filename(
            image.filename
        )

        upload_folder = os.path.join(
            BASE_DIR,
            "static",
            "uploads"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        image_path = os.path.join(
            upload_folder,
            filename
        )

        image.save(
            image_path
        )

        background = (
            "uploads/" + filename
        )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE page_settings

        SET
            background = ?,
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

    return redirect(
        url_for("settings_index")
    )


# =========================================================
# إعدادات صفحة المذكرة
# =========================================================

@app_Not.route(
    "/settings/note"
)
def settings_note():

    settings = get_page_settings(
        "note"
    )

    return render_template(
        "templates/settings_note.html",
        settings=settings
    )


# =========================================================
# حفظ إعدادات صفحة المذكرة
# =========================================================

@app_Not.route(
    "/save_settings/note",
    methods=["POST"]
)
def save_settings_note():

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

        SET
            background = ?,
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

    return redirect(
        url_for("settings_note")
    )


# =========================================================
# إعدادات صفحة التعديل
# =========================================================

@app_Not.route(
    "/settings/edit"
)
def settings_edit():

    settings = get_page_settings(
        "edit"
    )

    return render_template(
        "templates/settings_edit.html",
        settings=settings
    )


# =========================================================
# حفظ إعدادات صفحة التعديل
# =========================================================

@app_Not.route(
    "/save_settings/edit",
    methods=["POST"]
)
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

        SET
            background = ?,
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

    return redirect(
        url_for("settings_edit")
    )


# =========================================================
# إنشاء قاعدة البيانات
# =========================================================

create_table()


# =========================================================
# تشغيل الموقع
# =========================================================

if __name__ == "__main__":

    app_Not.run(
        debug=True
    )