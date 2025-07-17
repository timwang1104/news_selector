"""
Inoreader OAuth2认证处理
"""
import json
import os
import webbrowser
import secrets

from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlencode, urlparse, parse_qs
import requests

from ..config.settings import settings


class CallbackHandler(BaseHTTPRequestHandler):
    """处理OAuth回调的HTTP请求处理器"""

    def do_GET(self):
        """处理GET请求"""
        # 解析URL参数
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        # 检查是否有授权码
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.server.auth_state = query_params.get('state', [''])[0]

            # 返回成功页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>授权成功</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .success { color: #28a745; font-size: 24px; margin-bottom: 20px; }
                    .info { color: #6c757d; font-size: 16px; }
                </style>
            </head>
            <body>
                <div class="success">✅ 授权成功！</div>
                <div class="info">您可以关闭此页面，返回应用程序继续操作。</div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode('utf-8'))
        else:
            # 返回错误页面
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>授权失败</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .error { color: #dc3545; font-size: 24px; margin-bottom: 20px; }
                    .info { color: #6c757d; font-size: 16px; }
                </style>
            </head>
            <body>
                <div class="error">❌ 授权失败</div>
                <div class="info">请返回应用程序重试。</div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))

    def log_message(self, format, *args):
        """禁用日志输出"""
        pass


@dataclass
class UserToken:
    """用户认证令牌"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None


class InoreaderAuth:
    """Inoreader OAuth2认证管理器"""

    def __init__(self):
        self.config = settings.inoreader
        self.token: Optional[UserToken] = None
        self.current_state: Optional[str] = None  # 存储当前的state参数
        self._load_token()

    def _find_free_port(self) -> int:
        """找到一个可用的端口"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def _start_callback_server(self, port: int) -> HTTPServer:
        """启动回调服务器"""
        server = HTTPServer(('localhost', port), CallbackHandler)
        server.auth_code = None
        server.auth_state = None
        return server
    
    def _load_token(self) -> None:
        """从本地文件加载已保存的token"""
        try:
            if os.path.exists(settings.user_token_file):
                with open(settings.user_token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                    self.token = UserToken(**token_data)
        except Exception as e:
            print(f"加载token失败: {e}")
            self.token = None
    
    def _save_token(self) -> None:
        """保存token到本地文件"""
        if self.token:
            settings.ensure_cache_dir()
            try:
                with open(settings.user_token_file, 'w', encoding='utf-8') as f:
                    token_data = {
                        'access_token': self.token.access_token,
                        'refresh_token': self.token.refresh_token,
                        'token_type': self.token.token_type,
                        'expires_in': self.token.expires_in
                    }
                    json.dump(token_data, f, indent=2)
            except Exception as e:
                print(f"保存token失败: {e}")
    
    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """获取OAuth2认证URL"""
        if state is None:
            state = secrets.token_urlsafe(32)  # 生成随机state参数

        self.current_state = state  # 保存state用于验证

        params = {
            'client_id': self.config.app_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'read',
            'state': state
        }
        return f"{self.config.oauth_url}auth?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> bool:
        """使用授权码换取访问令牌"""
        token_url = f"{self.config.oauth_url}token"
        
        data = {
            'client_id': self.config.app_id,
            'client_secret': self.config.app_key,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        try:
            print(f"正在向 {token_url} 发送token请求...")
            print(f"使用重定向URI: {redirect_uri}")

            response = requests.post(token_url, data=data, timeout=settings.app.request_timeout)

            if response.status_code != 200:
                print(f"❌ HTTP错误 {response.status_code}: {response.text}")
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        if error_data.get('error') == 'redirect_uri_mismatch':
                            print("🔧 重定向URI不匹配！")
                            print("请确保在Inoreader开发者门户中设置了正确的重定向URI:")
                            print(f"   {redirect_uri}")
                        else:
                            print(f"错误详情: {error_data}")
                    except:
                        pass
                return False

            token_data = response.json()
            self.token = UserToken(
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=token_data.get('expires_in')
            )

            self._save_token()
            print("✅ Token获取成功")
            return True

        except requests.RequestException as e:
            print(f"❌ 网络请求失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        if not self.token or not self.token.refresh_token:
            return False
        
        token_url = f"{self.config.oauth_url}token"
        
        data = {
            'client_id': self.config.app_id,
            'client_secret': self.config.app_key,
            'grant_type': 'refresh_token',
            'refresh_token': self.token.refresh_token
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=settings.app.request_timeout)
            response.raise_for_status()
            
            token_data = response.json()
            self.token.access_token = token_data['access_token']
            if 'refresh_token' in token_data:
                self.token.refresh_token = token_data['refresh_token']
            if 'expires_in' in token_data:
                self.token.expires_in = token_data['expires_in']
            
            self._save_token()
            return True
            
        except requests.RequestException as e:
            print(f"刷新token失败: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.token is not None and bool(self.token.access_token)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        if not self.is_authenticated():
            raise ValueError("用户未认证")
        
        return {
            'Authorization': f'{self.token.token_type} {self.token.access_token}',
            'AppId': self.config.app_id,
            'AppKey': self.config.app_key
        }
    
    def logout(self) -> None:
        """登出，清除本地token"""
        self.token = None
        if os.path.exists(settings.user_token_file):
            try:
                os.remove(settings.user_token_file)
            except Exception as e:
                print(f"删除token文件失败: {e}")
    
    def start_auth_flow(self) -> bool:
        """启动完整的认证流程"""
        # 找到可用端口
        port = 8080
        redirect_uri = f"http://localhost:{port}"

        print("正在启动本地服务器接收认证回调...")
        print(f"本地服务器地址: {redirect_uri}")

        # 启动本地服务器
        try:
            server = self._start_callback_server(port)
        except OSError as e:
            print(f"❌ 无法启动本地服务器在端口 {port}: {e}")
            print("可能的原因:")
            print("1. 端口被其他程序占用")
            print("2. 防火墙阻止了端口访问")
            print("3. 权限不足")
            return False

        # 生成认证URL
        auth_url = self.get_auth_url(redirect_uri)

        print("正在打开浏览器进行认证...")
        print(f"如果浏览器未自动打开，请手动访问: {auth_url}")

        try:
            webbrowser.open(auth_url)
        except Exception as e:
            print(f"打开浏览器失败: {e}")

        print("\n请在浏览器中完成认证...")
        print("认证成功后，浏览器会显示成功页面，然后自动继续...")

        # 在单独线程中启动服务器
        import threading
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # 等待授权码
        import time
        timeout = 300  # 5分钟超时
        start_time = time.time()

        while server.auth_code is None and (time.time() - start_time) < timeout:
            time.sleep(1)

        # 停止服务器
        server.shutdown()

        if server.auth_code:
            # 验证state参数
            if hasattr(server, 'auth_state') and server.auth_state:
                if server.auth_state != self.current_state:
                    print("❌ State参数验证失败，可能存在CSRF攻击")
                    return False
                print("✅ State参数验证通过")
            else:
                print("⚠️  未收到state参数")

            print("✅ 收到授权码，正在交换访问令牌...")
            return self.exchange_code_for_token(server.auth_code, redirect_uri)
        else:
            print("❌ 认证超时或失败")
            return False
