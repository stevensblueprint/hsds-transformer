# HSDS Transformer
## Setup
Create a virtualenv
```bash
python3 -m venv .venv
```

Activate the virtualenv
```bash
source .venv/bin/activate
```

Install dependencies
```bash
pip3 install -r requirements.txt
```

## Running the api
```bash
uvicorn api.app:app --app-dir src --reload
```