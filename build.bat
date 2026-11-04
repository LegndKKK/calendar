@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv-build\Scripts\python.exe" (
    echo [1/3] 创建构建环境...
    python -m venv .venv-build || goto :error
    ".venv-build\Scripts\python.exe" -m pip install --upgrade pip || goto :error
    ".venv-build\Scripts\python.exe" -m pip install pyinstaller || goto :error
)

if not exist "static\icon.ico" (
    echo [2/3] 生成图标...
    python tools\make_icon.py || goto :error
)

echo [3/3] 构建单文件 exe...
".venv-build\Scripts\python.exe" -m PyInstaller ^
    --noconfirm --clean --onefile --windowed ^
    --name calendar ^
    --icon "static\icon.ico" ^
    --add-data "static;static" ^
    app.py || goto :error

echo.
echo 构建完成：dist\calendar.exe
echo 运行时数据目录：%LOCALAPPDATA%\LocalCalendar
pause
exit /b 0

:error
echo.
echo 构建失败。
pause
exit /b 1
