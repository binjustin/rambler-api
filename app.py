from flask import Flask, request, jsonify
import imaplib
import email
from email.header import decode_header
import os
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

# Hàm kết nối đến Rambler
def connect_to_rambler(username, password):
    imap_server = "imap.rambler.ru"
    mail = imaplib.IMAP4_SSL(imap_server)
    try:
        mail.login(username, password)
    except imaplib.IMAP4.error as e:
        raise Exception(f"Login failed: {str(e)}")
    return mail

# Hàm đọc email mới nhất chứa từ khóa tìm kiếm
def read_latest_email(mail, search_query=None):
    mail.select("inbox")
    
    if search_query:
        status, messages = mail.search(None, f'(SUBJECT "{search_query}")')
    else:
        status, messages = mail.search(None, "ALL")
    
    email_ids = messages[0].split()[:10]  # Lấy 10 email mới nhất
    
    if not email_ids:
        return None

    for email_id in email_ids[::-1]:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        email_message = email.message_from_bytes(msg_data[0][1])
        
        # Giải mã chủ đề
        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8", errors='replace')

        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() in ["text/plain", "text/html"]:
                    charset = part.get_content_charset()
                    body_bytes = part.get_payload(decode=True)
                    try:
                        body = body_bytes.decode(charset or "utf-8", errors='replace')
                    except Exception as e:
                        print(f"Error decoding part: {e}")
                    break
        else:
            body_bytes = email_message.get_payload(decode=True)
            charset = email_message.get_content_charset()
            try:
                body = body_bytes.decode(charset or "utf-8", errors='replace')
            except Exception as e:
                print(f"Error decoding single part: {e}")

        if search_query and search_query in subject:
            return {
                "subject": subject,
                "body": body,
                "id": email_id.decode()  # Trả về ID dưới dạng chuỗi
            }

    return None

# Hàm trích xuất mã xác minh từ nội dung email
def extract_verification_code(body):
    # Sử dụng BeautifulSoup để phân tích HTML
    soup = BeautifulSoup(body, 'html.parser')
    
    # Tìm đoạn văn bản chứa mã xác minh
    verification_text = soup.find(string=re.compile("To complete your request, enter the following verification code:"))
    
    if verification_text:
        # Tìm thẻ p tiếp theo chứa mã
        code_tag = verification_text.find_next('p')
        if code_tag:
            # Lấy mã từ thẻ p
            code = code_tag.text.strip()
            return code
    
    # Nếu không tìm thấy theo cách trên, thử tìm bằng regex
    match = re.search(r'\b\d{6}\b', body)
    if match:
        return match.group(0)
    
    return None
def delete_email(mail, email_id):
    mail.select("inbox")
    mail.store(email_id, '+FLAGS', '\\Deleted')
    mail.expunge()

@app.route('/get_verification_code', methods=['POST'])
def get_verification_code():
    data = request.json
    email_addr = data.get("email")
    password = data.get("password")
    search_query = data.get("search_query")

    if not email_addr or not password:
        return jsonify({"error": "Missing email or password."}), 400

    try:
        mail = connect_to_rambler(email_addr, password)
        latest_email = read_latest_email(mail, search_query=search_query)
        
        if latest_email:
            code = extract_verification_code(latest_email["body"])
            if code:
                response = {
                    "verification_code": code,
                    "latest_email": latest_email["subject"],
                    "email_id": latest_email["id"]
                }
                mail.logout()
                return jsonify(response)
            else:
                mail.logout()
                return jsonify({"message": "No verification code found."}), 404
        else:
            mail.logout()
            return jsonify({"message": "No email found matching the query."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/delete_email', methods=['POST'])
def delete_email_route():
    data = request.json
    email_addr = data.get("email")
    password = data.get("password")
    email_id = data.get("email_id")

    if not email_addr or not password or not email_id:
        return jsonify({"error": "Missing email, password, or email_id."}), 400

    try:
        mail = connect_to_rambler(email_addr, password)
        delete_email(mail, email_id)
        mail.logout()
        return jsonify({"message": "Email deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)