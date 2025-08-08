@echo off
echo Deleting old test.db...
del test.db 2>nul

echo Setting PYTHONPATH...
set PYTHONPATH=%cd%

echo Running pytest...
pytest -v

pause
