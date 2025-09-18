# FinancialManagement
### 安装库 
    #启动命令
    python3 run.py                                                      

    # 安装virtualenv工具，用于创建隔离的Python环境
    pip3 install virtualenv

    # 创建一个名为venv的虚拟环境
    virtualenv venv

    # 激活虚拟环境，以便在其中安装和使用包
    source venv/bin/activate

    # 退出虚拟环境
    deactivate

    # 导出依赖到requirements.txt
    pip freeze > requirements.txt

    安装依赖
    pip install -r requirements.txt