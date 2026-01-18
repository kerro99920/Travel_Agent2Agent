import os

# 项目根目录
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


#定义配置文件
class Config:
    def __init__(self):
        # 大模型配置
        self.base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        self.api_key = 'sk-67320312aa3e4fsdfsss3411aa0d7'
        self.model_name = 'qwen-plus'

        # 数据库配置
        self.host = 'localhost'
        self.user = 'root'
        self.password = 'root'
        self.database = 'travel_rag'

        # 日志配置
        self.log_file = os.path.join(project_root, 'SmartVoyage', 'logs/app.log')


if __name__ == '__main__':
    print(Config().log_file)