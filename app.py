import datetime
import hashlib
from datetime import datetime, timedelta

import jwt
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename

import requests

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

from pymongo import MongoClient
import certifi

ca = certifi.where()

client = MongoClient('mongodb+srv://test:sparta@cluster0.lovi7.mongodb.net/Cluster0?retryWrites=true&w=majority')
db = client.dbsparta  # dbsparta 는 변경


# 로그인
@app.route('/sign_in', methods=['POST'])
def sign_in():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    # 비밀번호 해시처리
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    # result가 none가 아니라면 토큰발행
    if result is not None:
        payload = {
            'id': username_receive,
            # 토큰 유지 시간
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# 회원가입
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    year_receive = request.form['year_give']
    month_receive = request.form['month_give']
    day_receive = request.form['day_give']
    sex_receive = request.form['sex_give']
    # 비밀번호 해시처리
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
        "year": year_receive,  # 출생연도
        "month": month_receive,  # 월
        "day": day_receive,  # 일
        "sex": sex_receive,  # 성별
        "profile_name": username_receive,  # 프로필 이름 기본값은 아이디
        "profile_pic": "",  # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지
        "profile_info": ""  # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


# id 형식, 존재여부 확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    # bool : 값이 있으면 true 없으면 false
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        print(user_info)
        return render_template('fork.html', user_info=user_info)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("home2", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("home2", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route('/home2')
def home2():
    return render_template('home.html')

@app.route('/mypage/<username>')
def mypage(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False

        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template('mypage.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/fork')
def fork():
    return render_template('fork.html')

@app.route('/festival')
def festival():
    r = requests.get(
        "http://api.data.go.kr/openapi/tn_pubr_public_cltur_fstvl_api?serviceKey=2%2FK1CdSKKycm%2FIyr1z09L2cFGNZIOO0uBgTNREIj3m8CbuZg5jcGqGzQV%2FhKIbphrEEOOeoxzwyj4vgco6M1bg%3D%3D&pageNo=0&numOfRows=100&type=json")
    response = r.json()
    items = response['response']['body']['items']
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        print(user_info)
        return render_template('festiv.html', user_info=user_info, items=items)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("home2", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("home2", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/review', methods=['POST'])
def comment_post():
    place_receive = request.form['place_give']
    comment_receive = request.form['comment_give']

    file = request.files["file_give"]

    extension = file.filename.split('.')[-1]

    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    filename = f'file-{mytime}'

    save_to = f'static/{filename}.{extension}'
    file.save(save_to)

    doc = {
        "place": place_receive,
        "comment": comment_receive,
        "file": f'{filename}.{extension}'
        }

    db.festivareview.insert_one(doc)

    return jsonify({'result': 'success', 'msg': f'"{place_receive}" 저장!'})

@app.route("/review", methods=["GET"])
def comment_get():
    comment_list = list(db.festivareview.find({}, {'_id': False}))
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        print(user_info)
        return render_template('review.html', user_info=user_info, rows=comment_list)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("home2", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("home2", msg="로그인 정보가 존재하지 않습니다."))



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
