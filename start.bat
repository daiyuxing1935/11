@echo off
chcp 65001 >nul
echo ============================================
echo   AI智能体学科学习平台 Demo 启动脚本
echo ============================================
echo.

:: 检查并安装 Python 依赖
echo [1/3] 检查后端依赖...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet 2>nul || (
    echo 默认源安装失败，尝试使用清华镜像...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)
echo [OK] Python 依赖已就绪

:: 检查并安装前端依赖
echo.
echo [2/3] 检查前端依赖...
cd /d "%~dp0frontend"
if not exist "node_modules\" (
    echo 正在安装前端依赖...
    call npm install
    echo [OK] 前端依赖安装完成
) else (
    echo [OK] 前端依赖已就绪
)

:: 启动后端
echo.
echo [3/3] 启动服务...
cd /d "%~dp0backend"
start "AI-Learning-Backend" cmd /c "cd /d %~dp0backend && python main.py"
echo [OK] 后端服务已启动 (端口 8000)

timeout /t 3 /nobreak >nul

:: 启动前端
cd /d "%~dp0frontend"
start "AI-Learning-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"
echo [OK] 前端服务已启动 (端口 5173)

echo.
echo ============================================
echo   启动完成! 请访问:
echo   前端页面: http://localhost:5173
echo   后端API:  http://localhost:8000/docs
echo   Demo账号: demo / demo123
echo.
echo   如后端启动失败，请确保已安装 Python 3.10+
echo   并手动运行: pip install -r backend\requirements.txt
echo ============================================
pause
