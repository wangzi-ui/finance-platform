@echo off
chcp 65001
echo ========================================
echo   智能投资分析平台 - 启动中...
echo ========================================
echo.

echo [1/2] 正在安装依赖包...
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [2/2] 正在启动平台...
echo 浏览器将自动打开，如未打开请访问: http://localhost:8501
echo.
python -m streamlit run main.py --server.port 8501

pause