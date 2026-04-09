python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
echo "Bootstrap complete. Next run: python -m auto_report.cli run-once"
