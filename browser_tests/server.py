"""Dedicated test server; OS selects and retains an available port."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
from waitress import create_server

server = create_server(app, host="127.0.0.1", port=0)
Path(sys.argv[1]).write_text(str(server.effective_port), encoding="utf-8")
server.run()
