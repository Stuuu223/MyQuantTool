@echo off
echo ========================================
echo MyQuantTool 依赖安装脚本
echo ========================================
echo.

echo [1/5] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)
echo Python环境检查通过
echo.

echo [2/5] 安装基础依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 警告: 基础依赖安装可能有问题，请检查网络连接
)
echo.

echo [3/5] 安装机器学习依赖...
echo 注意: TensorFlow安装可能需要较长时间，请耐心等待
pip install tensorflow>=2.13.0
if %errorlevel% neq 0 (
    echo 警告: TensorFlow安装失败，机器学习功能将不可用
    echo 您可以稍后手动安装: pip install tensorflow
)
echo.

echo [4/5] 安装强化学习依赖...
pip install xgboost>=2.0.0 gymnasium>=0.29.0
if %errorlevel% neq 0 (
    echo 警告: 强化学习依赖安装失败
)
echo.

echo [5/5] 安装HTTP请求库...
pip install requests>=2.31.0
if %errorlevel% neq 0 (
    echo 警告: requests库安装失败
)
echo.

echo ========================================
echo 依赖安装完成！
echo ========================================
echo.
echo 如果某些依赖安装失败，您可以：
echo 1. 检查网络连接
echo 2. 使用国内镜像源: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>
echo 3. 手动安装失败的包
echo.
echo 启动应用: streamlit run main.py
echo.
pause