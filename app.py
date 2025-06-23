from flask import Flask, request, jsonify

# Thay đổi key này thành một chuỗi bí mật của riêng bạn
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_change_me' 

# Thay thế bằng cơ sở dữ liệu thực tế sau này
# Tạm thời hardcode key để kiểm tra việc triển khai
VALID_KEYS = {
    "TEST-KEY-123": "2099-12-31",
    "ANOTHER-KEY-456": "2099-12-31"
}

@app.route('/')
def home():
    return "API Server is running. Use the /verify_key endpoint to check keys."

@app.route('/verify_key', methods=['POST'])
def verify_key():
    data = request.get_json()
    if not data or 'key' not in data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    user_key = data['key']
    
    if user_key in VALID_KEYS:
        expiry_date = VALID_KEYS[user_key]
        return jsonify({
            "status": "success",
            "key": user_key,
            "expiry_date": expiry_date
        })
    else:
        return jsonify({
            "status": "failure",
            "message": "Invalid or unknown key"
        })

if __name__ == '__main__':
    app.run()

