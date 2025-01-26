import os
import time
import requests
import threading
from flask import Flask, render_template, request, jsonify
import re  # Thêm import để sử dụng regex

app = Flask(__name__)

# Hàm kiểm tra trạng thái tài khoản Facebook
def check_live(uids, completed_uids, lock, live_count, die_count, total_count, live_uids, die_uids, completion_event, input_lines):
    for checkliveuid, uid in enumerate(uids, start=0):
        try:
            response = requests.get(f"https://graph.facebook.com/{uid}/picture?redirect=0", timeout=25)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'data' in data:
                        url = data['data'].get('url', '')
                        
                        if "static.xx" in url:
                            with lock:
                                die_count[0] += 1
                                die_uids.append(input_lines[checkliveuid])  # Lưu nguyên dòng vào die_uids
                        elif "scontent" in url:
                            with lock:
                                live_count[0] += 1
                                live_uids.append(input_lines[checkliveuid])  # Lưu nguyên dòng vào live_uids
                    else:
                        with lock:
                            die_count[0] += 1
                            die_uids.append(input_lines[checkliveuid])  # Lưu nguyên dòng vào die_uids
                except Exception as e:
                    with lock:
                        die_count[0] += 1
                        die_uids.append(input_lines[checkliveuid])  # Lưu nguyên dòng vào die_uids
            else:
                with lock:
                    die_count[0] += 1
                    die_uids.append(input_lines[checkliveuid])  # Lưu nguyên dòng vào die_uids

            with lock:
                total_count[0] += 1

        except requests.exceptions.RequestException as e:
            with lock:
                die_count[0] += 1
                die_uids.append(input_lines[checkliveuid])  # Lưu nguyên dòng vào die_uids

        with lock:
            completed_uids[0] += 1
            
            if completed_uids[0] == len(uids):
                completion_event.set()

def extract_uids(input_data):
    """Hàm để tách UID đầu tiên từ mỗi dòng trong chuỗi đầu vào"""
    uids = []
    input_lines = input_data.splitlines()  # Tách chuỗi đầu vào thành các dòng
    
    for line in input_lines:
        # Tìm UID hợp lệ trong dòng, chỉ lấy UID đầu tiên
        uid_match = re.match(r'\b\d{10,15}\b', line)  # Tìm chuỗi số 10-15 ký tự
        if uid_match:
            uids.append(uid_match.group())  # Thêm UID đầu tiên vào danh sách
    
    return uids, input_lines  # Trả về cả UID và các dòng đầy đủ

@app.route('/checkliveuid', methods=['GET'])
def checkliveuid():
    return render_template('checkliveuid.html')

@app.route('/check', methods=['POST'])
def check_status():
    data = request.get_json()
    input_data = data['uids']

    # Tách UID hợp lệ từ đầu vào và lấy các dòng đầu vào
    uids, input_lines = extract_uids(input_data)

    if not uids:
        return jsonify(error="No valid UID found in the input.")

    completed_uids = [0]
    live_count = [0]
    die_count = [0]
    total_count = [0]
    live_uids = []
    die_uids = []

    completion_event = threading.Event()
    lock = threading.Lock()

    batch_size = 10
    uid_batches = [uids[i:i + batch_size] for i in range(0, len(uids), batch_size)]

    threads = []
    for batch in uid_batches:
        thread = threading.Thread(target=check_live, args=(batch, completed_uids, lock, live_count, die_count, total_count, live_uids, die_uids, completion_event, input_lines))
        thread.start()
        threads.append(thread)
        time.sleep(2)

    completion_event.wait()

    for thread in threads:
        thread.join()

    # Trả về kết quả và số lượng live/die
    return jsonify(
        live_uids=live_uids,
        die_uids=die_uids,
        live_count=live_count[0],
        die_count=die_count[0]
    )

if __name__ == '__main__':
    app.run(debug=True)
