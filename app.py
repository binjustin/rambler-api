from flask import Flask, request, jsonify
import imaplib
import email
from email.header import decode_header
import os

app = Flask(__name__)

# Hàm kết nối đến Rambler
def connect_to_rambler(username, password):
    imap_server = "imap.rambler.ru"
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(username, password)
    return mail

# Hàm đọc email mới nhất chứa từ khóa tìm kiếm
def read_latest_email(mail, search_query=None):
    mail.select("inbox")
    
    if search_query:
        status, messages = mail.search(None, f'(SUBJECT "{search_query}")')
    else:
        status, messages = mail.search(None, "ALL")
    
    email_ids = messages[0].split()
    
    if not email_ids:
        return None

    for email_id in email_ids[::-1]:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        if search_query in subject:
            return {
                "subject": subject,
                "body": body
            }

    return None

@app.route('/')
def home():
    return "Welcome to the Rambler Email Reader API!"

@app.route('/read_emails', methods=['POST'])
def get_latest_email():
    data = request.json
    email_addr = data.get("email")
    password = data.get("password")
    search_query = data.get("search_query")

    try:
        mail = connect_to_rambler(email_addr, password)
        latest_email = read_latest_email(mail, search_query=search_query)
        mail.logout()
        
        if latest_email:
            return jsonify({
                "latest_email": latest_email["subject"],
                "email_body": latest_email["body"]
            })
        else:
            return jsonify({"message": "No email found matching the query."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
