python -m venv .venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

python app.py


Bedienung mit Handy: http://localhost:5000/

Ausschank-Monitor: http://localhost:5000/monitor