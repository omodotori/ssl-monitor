@echo off
REM Активируем виртуальное окружение
call D:\Projects\ssl_monitor\venv\Scripts\activate.bat

REM Запускаем скрипт без консоли
D:\Projects\ssl_monitor\venv\Scripts\pythonw.exe D:\Projects\ssl_monitor\ssl_monitor.py

exit
