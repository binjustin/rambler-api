from flask import Flask, request, jsonify
import imaplib
import email
from email.header import decode_header

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
    
    # Tìm kiếm tất cả các email, hoặc email có chứa từ khóa tìm kiếm
    if search_query:
        status, messages = mail.search(None, f'(SUBJECT "{search_query}")')
    else:
        status, messages = mail.search(None, "ALL")
    
    email_ids = messages[0].split()
    
    # Nếu không tìm thấy email phù hợp
    if not email_ids:
        return None

    # Duyệt qua các email từ mới nhất (email cuối cùng trong danh sách)
    for email_id in email_ids[::-1]:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        # Lấy tiêu đề của email và giải mã nếu cần
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")
        
        # Lấy nội dung của email
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Kiểm tra nếu email có chứa từ khóa
        if search_query in subject:
            return {
                "subject": subject,
                "body": body  # Trả về cả tiêu đề và nội dung email
            }

    return None  # Nếu không tìm thấy email nào phù hợp

# Endpoint để đọc email mới nhất chứa từ khóa
@app.route('/read_emails', methods=['POST'])
def get_latest_email():
    data = request.json
    email_addr = data.get("email")
    password = data.get("password")
    search_query = data.get("search_query")  # Lấy từ khóa tìm kiếm

    try:
        # Kết nối đến hộp thư Rambler
        mail = connect_to_rambler(email_addr, password)
        
        # Lấy email mới nhất chứa từ khóa
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
    app.run(debug=True)
