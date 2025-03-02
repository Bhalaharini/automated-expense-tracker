from flask import Flask, request, render_template, redirect, url_for
import pymysql
import csv
import os

app = Flask(__name__)

# Database Connection (Use environment variables for security in production)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Adhisince2005%",  # Replace with your secure password
    "database": "aet"
}

# File Upload Configuration
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/")
def index():
    """
    Renders the main page (index.html) which contains:
      - A form for submitting user details (/submit)
      - A form for uploading a CSV file (/upload)
    """
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    """Handles the user details form submission."""
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")

    if not name or not email or not phone:
        return "All fields (name, email, phone) are required!", 400

    try:
        db = pymysql.connect(**DB_CONFIG)
        with db.cursor() as cursor:
            # Example insert into the 'users' table (using phone as 'password' for illustration)
            insert_query = """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (name, email, phone))
            db.commit()
        db.close()

        # Display a success message and a link back to the main page ("/")
        return '''
            <h2>User data saved successfully!</h2>
            <p><a href="/">Go to CSV Upload Page</a></p>
        '''
    except Exception as e:
        return f"Error: {e}", 500

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handles CSV file uploads and stores transaction data in the DB."""
    if "file" not in request.files:
        return "No file part"

    file = request.files["file"]
    if file.filename == "":
        return "No selected file"

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    try:
        db = pymysql.connect(**DB_CONFIG)
        with db.cursor() as cursor:
            with open(file_path, "r") as csv_file:
                reader = csv.DictReader(csv_file)  # Expecting CSV headers: date, description, amount, category_name

                for row in reader:
                    date = row["date"]
                    description = row["description"]
                    amount = float(row["amount"])
                    category_name = row["category_name"]
                    user_id = 1  # Assuming default user; modify as needed

                    # Insert category if not exists
                    cursor.execute("SELECT id FROM categories WHERE category_name = %s", (category_name,))
                    category = cursor.fetchone()
                    if category:
                        category_id = category[0]
                    else:
                        cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category_name,))
                        db.commit()
                        category_id = cursor.lastrowid

                    # Insert transaction
                    cursor.execute(
                        """INSERT INTO transactions
                           (user_id, date, description, amount, category_id)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (user_id, date, description, amount, category_id)
                    )
                    db.commit()
        db.close()
        # After uploading, redirect to the chart page
        return redirect(url_for('chart'))
    except Exception as e:
        return f"Error: {e}"

@app.route("/chart")
def chart():
    """Queries the database and renders a pie chart of expenses by category."""
    try:
        db = pymysql.connect(**DB_CONFIG)
        with db.cursor() as cursor:
            query = """
                SELECT c.category_name, SUM(t.amount) as total_amount
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = 1
                GROUP BY c.category_name
            """
            cursor.execute(query)
            data = cursor.fetchall()
        db.close()

        labels = [row[0] for row in data]
        values = [float(row[1]) for row in data]

        return render_template("chart.html", labels=labels, values=values)
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    app.run(debug=True)
