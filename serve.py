import os
from waitress import serve
from main import app
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/waitress.log")
    ]
)
logger = logging.getLogger('waitress')

if __name__ == '__main__':
    # 获取配置参数（可以从环境变量读取）
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    threads = int(os.environ.get('THREADS', 2))
    
    logger.info(f"Starting Waitress server on {host}:{port} with {threads} threads")
    
    # 启动Waitress服务器
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        url_scheme='http'
    )