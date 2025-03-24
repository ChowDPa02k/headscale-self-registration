from flask import Blueprint, current_app, render_template, request, redirect, url_for, session
import requests
import yaml
import json

jbp = Blueprint('jellyfin', __name__)

def load_config():
    """从配置文件加载Jellyfin配置"""
    try:
        with open('./jellyfin_conf.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        current_app.logger.error(f"Failed to load config: {e.__class__.__name__} {str(e)}")
        return None

def api_request(method, endpoint, headers=None, data=None, json_data=None):
    """统一处理Jellyfin API请求和错误处理"""
    config = load_config()
    if not config:
        return False, None, None, "Failed to load configuration"
    
    server_url = config.get('server', '')
    api_key = config.get('api_key', '')
    
    if headers is None:
        headers = {}
    
    if 'Authorization' not in headers:
        headers['Authorization'] = f'MediaBrowser Token="{api_key}"'
    
    url = f"{server_url}{endpoint}"
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            json=json_data,
            verify=False
        )
        
        status_code = response.status_code
        
        # 尝试解析响应内容为JSON
        response_body = None
        try:
            if response.content:
                response_body = response.json()
        except json.JSONDecodeError:
            response_body = response.text if response.text else None
        
        # 错误处理
        if status_code not in (200, 204):
            error_message = ""
            if status_code == 401:
                error_message = "Authentication failed: API token is invalid or expired"
            elif status_code == 403:
                error_message = "Permission denied: Not authorized to perform this operation"
            elif status_code == 400:
                if response_body and isinstance(response_body, dict) and 'errors' in response_body:
                    error_details = []
                    for field, errors in response_body['errors'].items():
                        error_details.append(f"{field}: {', '.join(errors)}")
                    error_message = f"Bad request: {'; '.join(error_details)}"
                else:
                    error_message = "Bad request: Invalid parameters"
            else:
                error_message = f"HTTP {status_code}"
            
            current_app.logger.error(f"API request failed: {error_message}")
            return False, response_body, status_code, error_message
        
        return True, response_body, status_code, None
        
    except requests.RequestException as e:
        current_app.logger.error(f"Request exception: {e.__class__.__name__} {str(e)}")
        return False, None, None, f"Connection error: {str(e)}"

def get_jellyfin_folders():
    """获取Jellyfin媒体文件夹列表"""
    success, response_body, status_code, error_message = api_request(
        method="GET",
        endpoint="/Library/MediaFolders?IsHidden=false"
    )
    
    if not success:
        current_app.logger.error(f"Failed to get Jellyfin folders: {error_message}")
        return None, None, None
    
    # 所有文件夹的ID和名称映射
    all_folders = {item['Name']: item['Id'] for item in response_body.get('Items', [])}
    all_folder_ids = [item['Id'] for item in response_body.get('Items', [])]
    
    # 加载配置获取NSFW和禁用内容列表
    config = load_config()
    if not config:
        return None, None, None
        
    nsfw_contents = config.get('nsfw_contents', [])
    disabled_contents = config.get('disabled_contents', [])
    
    # NSFW内容文件夹ID列表
    nsfw_folders = [all_folders[name] for name in nsfw_contents if name in all_folders]
    
    # 默认不启用的文件夹ID列表
    disabled_folders = [all_folders[name] for name in disabled_contents if name in all_folders]
    
    return all_folder_ids, nsfw_folders, disabled_folders

def create_jellyfin_user(username, password):
    """创建Jellyfin用户"""
    headers = {
        'Content-Type': 'application/json'
    }
    
    user_data = {
        "Name": username,
        "Password": password
    }
    
    success, response_body, status_code, error_message = api_request(
        method="POST",
        endpoint="/Users/New",
        headers=headers,
        json_data=user_data
    )
    
    if not success:
        if status_code == 400:
            error_message = f"User `{username}` already exists or username contains illegal characters"
        
        current_app.logger.error(f"Failed to create user: {error_message}")
        return False, error_message
    
    return True, response_body

def set_user_policy(user_id, allow_nsfw, need_transcoding, need_downloading, all_folder_ids, nsfw_folders, disabled_folders):
    """设置用户权限策略"""
    # 计算启用的文件夹ID列表
    enabled_folders = list(all_folder_ids)
    
    # 从启用的文件夹中排除disabled_folders
    for folder_id in disabled_folders:
        if folder_id in enabled_folders:
            enabled_folders.remove(folder_id)
    
    # 如果不允许NSFW，从启用的文件夹中排除nsfw_folders
    if not allow_nsfw:
        for folder_id in nsfw_folders:
            if folder_id in enabled_folders:
                enabled_folders.remove(folder_id)
    
    # 设置用户策略
    policy_data = {
        "IsAdministrator": False,
        "IsHidden": True,
        "EnableCollectionManagement": False,
        "EnableSubtitleManagement": False,
        "EnableLyricManagement": False,
        "IsDisabled": False,
        "BlockedTags": [],
        "AllowedTags": [],
        "EnableUserPreferenceAccess": True,
        "AccessSchedules": [],
        "BlockUnratedItems": [],
        "EnableRemoteControlOfOtherUsers": False,
        "EnableSharedDeviceControl": True,
        "EnableRemoteAccess": True,
        "EnableLiveTvManagement": True,
        "EnableLiveTvAccess": True,
        "EnableMediaPlayback": True,
        "EnableAudioPlaybackTranscoding": True,
        "EnableVideoPlaybackTranscoding": need_transcoding,
        "EnablePlaybackRemuxing": True,
        "ForceRemoteSourceTranscoding": False,
        "EnableContentDeletion": False,
        "EnableContentDeletionFromFolders": [],
        "EnableContentDownloading": need_downloading,
        "EnableSyncTranscoding": True,
        "EnableMediaConversion": True,
        "EnabledDevices": [],
        "EnableAllDevices": True,
        "EnabledChannels": [],
        "EnableAllChannels": True,
        "EnabledFolders": enabled_folders,
        "EnableAllFolders": False,
        "InvalidLoginAttemptCount": 0,
        "LoginAttemptsBeforeLockout": -1,
        "MaxActiveSessions": 0,
        "EnablePublicSharing": True,
        "BlockedMediaFolders": [],
        "BlockedChannels": [],
        "RemoteClientBitrateLimit": 0,
        "AuthenticationProviderId": "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
        "PasswordResetProviderId": "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider",
        "SyncPlayAccess": "CreateAndJoinGroups"
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    success, response_body, status_code, error_message = api_request(
        method="POST",
        endpoint=f"/Users/{user_id}/Policy",
        headers=headers,
        json_data=policy_data
    )
    
    if not success:
        current_app.logger.error(f"Failed to set user policy: {error_message}")
        return False, error_message
    
    return True, "User policy set successfully"

def set_user_configuration(user_id, allow_nsfw_continue, nsfw_folders):
    """设置用户配置，如果不允许NSFW内容在继续观看中显示，则设置排除项"""
    if allow_nsfw_continue:
        return True, "No need to set configuration"
    
    # 设置用户配置
    config_data = {
        "AudioLanguagePreference": "",
        "PlayDefaultAudioTrack": True,
        "SubtitleLanguagePreference": "chi",
        "DisplayMissingEpisodes": False,
        "GroupedFolders": [],
        "SubtitleMode": "Smart",
        "DisplayCollectionsView": False,
        "EnableLocalPassword": False,
        "LatestItemsExcludes": nsfw_folders,
        "MyMediaExcludes": [],
        "HidePlayedInLatest": True,
        "RememberAudioSelections": True,
        "RememberSubtitleSelections": True,
        "EnableNextEpisodeAutoPlay": True
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    success, response_body, status_code, error_message = api_request(
        method="POST",
        endpoint=f"/Users/{user_id}/Configuration",
        headers=headers,
        json_data=config_data
    )
    
    if not success:
        current_app.logger.error(f"Failed to set user configuration: {error_message}")
        return False, error_message
    
    return True, "User configuration set successfully"

@jbp.route('/', methods=['GET'])
def index_jellyfin():
    result = session.pop('result', None)
    return render_template('jellyfin.html', result=result)

@jbp.route('/register', methods=['POST'])
def register_jellyfin():
    username = request.form.get('username')
    password = request.form.get('password')
    allow_nsfw = request.form.get('allow_nsfw') == 'on'
    allow_nsfw_continue = request.form.get('allow_nsfw_continue') == 'on'
    need_transcoding = request.form.get('need_transcoding') == 'on'
    need_downloading = request.form.get('need_downloading') == 'on'
    
    current_app.logger.info(f"Received registration request for user: {username}")
    
    # 获取Jellyfin文件夹信息
    all_folder_ids, nsfw_folders, disabled_folders = get_jellyfin_folders()
    if not all_folder_ids:
        session['result'] = "Failed to retrieve Jellyfin folders information"
        return redirect(url_for('jellyfin.index_jellyfin'))
    
    # 创建用户
    success, user_data = create_jellyfin_user(username, password)
    if not success:
        session['result'] = f"Failed to create user: {user_data}"
        return redirect(url_for('jellyfin.index_jellyfin'))
    
    user_id = user_data.get('Id')
    if not user_id:
        session['result'] = f"Failed to get user ID from response"
        return redirect(url_for('jellyfin.index_jellyfin'))
    
    # 设置用户策略
    success, message = set_user_policy(
        user_id, 
        allow_nsfw, 
        need_transcoding, 
        need_downloading,
        all_folder_ids,
        nsfw_folders,
        disabled_folders
    )
    
    if not success:
        session['result'] = f"User created but failed to set policy: {message}"
        # current_app.logger.warning(f"User created but failed to set policy: {message}")
        return redirect(url_for('jellyfin.index_jellyfin'))
    
    # 如果没有选择允许NSFW内容在继续观看中显示，则设置用户配置
    if allow_nsfw and not allow_nsfw_continue:
        success, message = set_user_configuration(user_id, allow_nsfw_continue, nsfw_folders)
        if not success:
            session['result'] = f"User created and policy set, but failed to set configuration: {message}"
            # current_app.logger.warning(f"User created and policy set, but failed to set configuration: {message}")
            return redirect(url_for('jellyfin.index_jellyfin'))
    
    session['result'] = f"User '{username}' created successfully with ID: {user_id}"
    # current_app.logger.info(f"User '{username}' created successfully with ID: {user_id}")
    
    return redirect(url_for('jellyfin.index_jellyfin'))