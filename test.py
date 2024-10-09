import requests

url = "http://127.0.0.1:5000/read_emails"  # Đúng URL của API

# Thay đổi thông tin email và mật khẩu của bạn
email_addr = "rmgegutcij@rambler.ru"  # Thay thế bằng địa chỉ email của bạn
password = "9071594apLfLT"  # Thay thế bằng mật khẩu email của bạn
search_query = "code"  # Thay thế từ khóa nếu cần

# Dữ liệu gửi trong yêu cầu POST
payload = {
    "email": email_addr,
    "password": password,
    "search_query": search_query
}

# Gửi yêu cầu POST với dữ liệu JSON
response = requests.post(url, json=payload)

# In kết quả phản hồi từ server
if response.status_code == 200:
    print("Tiêu đề email mới nhất:", response.json().get("latest_email"))
    print("Nội dung email:", response.json().get("email_body"))
else:
    print("Lỗi:", response.json().get("error") or response.json().get("message"))
