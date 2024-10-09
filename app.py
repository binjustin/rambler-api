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
        
        # Giải mã chủ đề
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8", errors='replace')

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                # Kiểm tra loại phần
                if part.get_content_type() == "text/plain" or part.get_content_type() == "text/html":
                    charset = part.get_content_charset()
                    body_bytes = part.get_payload(decode=True)
                    try:
                        # Giải mã với charset hoặc mặc định là utf-8
                        body = body_bytes.decode(charset or "utf-8", errors='replace')
                    except Exception as e:
                        print(f"Error decoding part: {e}")
                    break
        else:
            body_bytes = msg.get_payload(decode=True)
            charset = msg.get_content_charset()
            try:
                body = body_bytes.decode(charset or "utf-8", errors='replace')
            except Exception as e:
                print(f"Error decoding single part: {e}")

        if search_query and search_query in subject:
            return {
                "subject": subject,
                "body": body
            }

    return None

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
