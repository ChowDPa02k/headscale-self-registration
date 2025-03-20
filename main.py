from flask import Flask, render_template, request, redirect, url_for, session
import subprocess
import json
import secrets
import os
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

user_list_file = '/root/headscale_users.json'

if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/headscale_app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('App starting...')

def get_headscale_users(src='headscale'):
    """获取headscale用户列表"""
    ret = []

    if src == 'headscale':
        try:
            output = subprocess.run(['headscale', 'user', 'list', '-ojson'], 
                                capture_output=True, text=True, check=True)
            users = json.loads(output.stdout)
            with open(user_list_file, 'w') as f:
                f.write(output.stdout)
            ret = users
        except Exception as e:
            app.logger.error(f"Failed to get users: {e.__class__.__name__} {str(e)}")

    if src == 'file':
        try:
            with open(user_list_file, 'r') as f:
                users = json.load(f)
                ret = users
        except Exception as e:
            app.logger.error(f"Failed to get users from local: {e.__class__.__name__} {str(e)}")

    return ret

def create_user(username):
    """创建新用户"""
    try:
        output = subprocess.run(['headscale', 'users', 'create', username],
                               capture_output=True, text=True)
        if output.returncode == 0:
            return True, output.stdout
        else:
            return False, output.stderr
    except Exception as e:
        return False, str(e)

@app.route('/', methods=['GET'])
def index():
    # 获取用户列表
    users = get_headscale_users(src='file')
    user_names = [user['name'] for user in users] if users else ['default']
    
    # 从会话中获取结果（如果有）
    result = session.pop('result', None)
    
    return render_template('index.html', users=user_names, result=result)

@app.route('/register', methods=['POST'])
def register():
    result = ""
    
    users = get_headscale_users(src='file')
    user_names = [user['name'] for user in users] if users else ['default']

    node_id = request.form.get('node_id')
    user_type = request.form.get('user_type')
    app.logger.info(f"Received request: Node ID={node_id}, User={user_type}")
    
    if user_type not in user_names:
        success, output = create_user(user_type)
        if not success:
            result += f"Failed to create user: {output}"
            app.logger.warning(result)
            session['result'] = result
            return redirect(url_for('index'))
        else:
            result += f"Success: {output}\n"
            # 更新用户列表
            get_headscale_users
            # user_names = [user['name'] for user in users] if users else ['default']
    
    try:
        cmd = ['headscale', 'nodes', 'register', '--user', user_type, '--key', node_id]
        output = subprocess.run(cmd, capture_output=True, text=True)
        
        if output.returncode == 0:
            result += f"Success: {output.stdout}"
            app.logger.info(f"Success Register: {output.stdout}")
        else:
            result += f"Failed: {output.stderr}"
            app.logger.warning(f"Failed Register: {output.stderr}")
    except Exception as e:
        result += f"FATAL: {str(e)}"
        app.logger.warning(f"FATAL: {e.__class__.__name__} {str(e)}")
    
    session['result'] = result
    return redirect(url_for('index'))