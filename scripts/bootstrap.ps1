python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
Write-Host "Bootstrap complete. Next run: python -m auto_report.cli run-once"

