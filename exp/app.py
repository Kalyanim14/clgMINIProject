from flask import Flask, render_template, request, send_from_directory
import os
import cv2
import mysql.connector
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join('../static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MySQL configuration (update these with your credentials)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sharvan8',
    'database': 'image_encryption'
}

# Encryption function
def encrypt_message(image_path, output_path, message):
    img = cv2.imread(image_path)
    if img is None:
        return "Error: Could not open image."

    d = {chr(i): i for i in range(255)}
    if len(message) > img.shape[0] * img.shape[1]:
        return "Error: Message too long for the image size."

    img[0, 0] = [len(message), 0, 0]
    n, m, z = 0, 0, 0
    for i, char in enumerate(message):
        n, m = divmod(i + 1, img.shape[1])
        img[n, m, z] = d.get(char, 0)
        z = (z + 1) % 3

    success = cv2.imwrite(output_path, img)
    return None if success else "Error: Failed to save encrypted image."

# Decryption function
def decrypt_message(image_path, entered_password, image_id):
    if not os.path.exists(image_path):
        return "Error: Encrypted image file not found."

    img = cv2.imread(image_path)
    if img is None:
        return "Error: Could not open or find the image."

    c = {i: chr(i) for i in range(255)}

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM image_data WHERE image_id = %s", (image_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        return "Error: Image ID not found."
    if entered_password != result[0]:
        return "YOU ARE NOT AUTHORIZED!"

    msg_length = img[0, 0, 0]
    message, n, m, z = "", 0, 0, 0
    for i in range(msg_length):
        n, m = divmod(i + 1, img.shape[1])
        message += c.get(img[n, m, z], '?')
        z = (z + 1) % 3

    return message

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encrypt', methods=['GET', 'POST'])
def encrypt():
    if request.method == 'POST':
        image = request.files.get('image')
        message = request.form.get('message')
        password = request.form.get('password')

        if not image or not allowed_file(image.filename):
            return render_template('encrypt.html', error="Invalid image file.")
        if not message or not password:
            return render_template('encrypt.html', error="All fields are required.")

        unique_filename = f"{uuid.uuid4()}.png"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"encrypted_{unique_filename}")
        image.save(input_path)

        error = encrypt_message(input_path, output_path, message)
        if error:
            return render_template('encrypt.html', error=error)

        image_id = str(uuid.uuid4())
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO image_data (image_id, image_name, password) VALUES (%s, %s, %s)",
                           (image_id, unique_filename, password))
            conn.commit()
            cursor.close()
            conn.close()

            return render_template('encrypt.html', success=True,
                                   output_image=f"encrypted_{unique_filename}", image_id=image_id)
        except Exception as e:
            return render_template('encrypt.html', error=f"MySQL Error: {str(e)}")

    return render_template('encrypt.html')

@app.route('/decrypt', methods=['GET', 'POST'])
def decrypt():
    if request.method == 'POST':
        image = request.files.get('image')
        password = request.form.get('password')
        image_id = request.form.get('image_id')

        if not image or not allowed_file(image.filename):
            return render_template('decrypt.html', result="Invalid image file.")
        if not password or not image_id:
            return render_template('decrypt.html', result="All fields are required.")

        input_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
        image.save(input_path)

        result = decrypt_message(input_path, password, image_id)
        return render_template('decrypt.html', result=result)

    return render_template('decrypt.html')

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
