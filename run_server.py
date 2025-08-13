import http.server
import socketserver
import os

# --- 配置 ---
PORT = 9000
# 你想要作为服务器根目录的文件夹名称
DIRECTORY = "html" 

class Handler(http.server.SimpleHTTPRequestHandler):
    """
    一个简单的请求处理器，它会以 DIRECTORY 文件夹为根目录。
    """

    extensions_map = http.server.SimpleHTTPRequestHandler.extensions_map.copy()
    extensions_map.update({
        '.js': 'application/javascript'
    })
    
    def __init__(self, *args, **kwargs):
        # 在初始化时，将工作目录切换到我们指定的文件夹
        super().__init__(*args, directory=DIRECTORY, **kwargs)

# 检查指定的目录是否存在
if not os.path.isdir(DIRECTORY):
    print(f"错误: 文件夹 '{DIRECTORY}' 不存在。")
    print(f"请在脚本所在目录下创建一个名为 '{DIRECTORY}' 的文件夹。")
    exit()

# 使用 socketserver 来创建 TCP 服务器
# TCPServer 会将每个请求交给我们的 Handler 处理
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    # 获取服务器的实际地址和端口
    host, port = httpd.server_address
    
    print("=====================================================")
    print(f" 本地服务器已启动！")
    print(f" 根目录: '{os.path.abspath(DIRECTORY)}'")
    print(f" 请在浏览器中打开以下地址进行访问:")
    print(f"   => http://localhost:{PORT}")
    print(f"   => http://127.0.0.1:{PORT}")
    print("=====================================================")
    print("按 Ctrl+C 停止服务器。")
    
    # 启动服务器，它会一直运行直到你手动停止（例如按 Ctrl+C）
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
        httpd.shutdown()