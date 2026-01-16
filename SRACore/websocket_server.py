import asyncio
import json
import threading

from loguru import logger
import websockets
# from SRACore.util.config import load_app_config
# import importlib
# package = load_app_config().get('websockets', {}).get('package', 'websockets')
# websockets = importlib.import_module(package)

class WebSocketServer:
    def __init__(self, cli):
        """
        初始化WebSocket服务器
        :param cli: SRACli实例，用于执行命令
        """
        self.cli = cli
        self.server = None
        self.stop_event = threading.Event()
        self.host = '0.0.0.0'
        self.port = 8765
        self.thread = None
        self.connections: set = set()
        self.log_queue = None

    async def handle_connection(self, websocket):
        """
        处理WebSocket连接
        :param websocket: WebSocket连接对象
        """
        self.connections.add(websocket)
        logger.debug(f"WebSocket client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.connections.remove(websocket)
            logger.debug(f"WebSocket client disconnected from {websocket.remote_address}")

    async def handle_message(self, websocket, message):
        """
        处理接收到的消息
        :param websocket: WebSocket连接对象
        :param message: 接收到的消息
        """
        try:
            data = json.loads(message)
            command = data.get('command')
            args = data.get('args', '')
            
            if not command:
                await websocket.send(json.dumps({
                    'success': False,
                    'message': 'No command provided'
                }))
                return
            
            # 执行命令并获取结果
            result = await self.execute_command(command, args)
            
            await websocket.send(json.dumps({
                'success': True,
                'message': 'Command executed successfully',
                'result': result
            }))
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'success': False,
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'success': False,
                'message': f'Error: {str(e)}'
            }))

    async def execute_command(self, command, args):
        """
        执行命令
        :param command: 命令名称
        :param args: 命令参数
        :return: 命令执行结果
        """
        # 捕获标准输出
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            # 执行命令
            cmd_method = getattr(self.cli, f'do_{command}', None)
            if cmd_method:
                try:
                    result = cmd_method(args)
                    # 对于exit命令，特殊处理
                    if command == 'exit' and result:
                        return 'Exiting...'
                except Exception as e:
                    return f'Error executing command: {str(e)}'
            else:
                return f'Unknown command: {command}'
        
        # 获取标准输出
        output = f.getvalue()
        return output.strip()

    async def start_server(self):
        """
        启动WebSocket服务器
        """
        async with websockets.serve(self.handle_connection, self.host, self.port):
            logger.debug(f"WebSocket server started on ws://{self.host}:{self.port}")
            # 等待停止事件
            while not self.stop_event.is_set():
                await asyncio.sleep(0.1)
                if self.log_queue.empty():
                    continue
                msg = self.log_queue.get()
                for client in self.connections:
                    await client.send(msg)
            logger.debug("WebSocket server stopping...")

    def run(self):
        """
        在新线程中运行WebSocket服务器
        """
        asyncio.run(self.start_server())

    def start(self):
        """
        启动WebSocket服务器
        """
        if not self.thread or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            logger.debug("WebSocket server thread started")

    def stop(self):
        """
        停止WebSocket服务器
        """
        if self.stop_event:
            self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            logger.debug("WebSocket server thread stopped")

    def is_alive(self):
        return self.thread and self.thread.is_alive()