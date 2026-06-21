@echo off
chcp 65001 >nul
echo ========================================
echo   题库答题助手 - PyInstaller 打包脚本
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 安装依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [警告] pip安装部分失败，尝试继续...
)

REM 清理旧构建
echo [2/3] 清理旧构建...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM PyInstaller打包
echo [3/3] 开始打包（文件夹模式，方便U盘携带）...

pyinstaller ^
    --name="AnswerTool" ^
    --add-data="ocr_models;ocr_models" ^
    --add-data="data;data" ^
    --hidden-import=paddleocr ^
    --hidden-import=paddle ^
    --hidden-import=rapidfuzz ^
    --hidden-import=openpyxl ^
    --hidden-import=rarfile ^
    --hidden-import=requests ^
    --hidden-import=PIL ^
    --hidden-import=mss ^
    --collect-all paddleocr ^
    --collect-all paddle ^
    --noconsole ^
    --onedir ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   打包成功！
    echo   输出目录: dist\AnswerTool\
    echo   将整个 AnswerTool 文件夹复制到U盘即可
    echo ========================================
) else (
    echo.
    echo [错误] 打包失败，请检查错误信息
)

pause
