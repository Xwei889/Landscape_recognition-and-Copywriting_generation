from modules.flask_api import app
from waitress import serve

if __name__ == '__main__':
    print("🚀 服务器已启动，访问地址：http://127.0.0.1:5000")
    serve(app, host='127.0.0.1', port=5000)