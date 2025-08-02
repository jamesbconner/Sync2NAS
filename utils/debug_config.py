import configparser
from pathlib import Path
import tempfile
from sync2nas_config import load_configuration

# Create test config like in conftest.py
temp_dir = Path(tempfile.gettempdir()) / "test_sync2nas"
temp_dir.mkdir(parents=True, exist_ok=True)

config_path = temp_dir / "test_sync2nas_config.ini"
config = configparser.ConfigParser()

config["Database"] = {"type": "sqlite"}
config["SQLite"] = {"db_file": str(temp_dir / "test.db")}
config["Routing"] = {"anime_tv_path": str(temp_dir / "anime_tv_path")}
config["Transfers"] = {"incoming": str(temp_dir / "incoming")}
config["SFTP"] = {
    "host": "localhost",
    "port": "22",
    "username": "testuser",
    "ssh_key_path": str(temp_dir / "test_key"),
    "paths": "/remote"
}
config["TMDB"] = {"api_key": "test_api_key"}
config["llm"] = {"service": "ollama"}
config["ollama"] = {"model": "llama3.2"}

with config_path.open("w") as config_file:
    config.write(config_file)

print(f"Config written to: {config_path}")
print(f"Original sections: {list(config.keys())}")

# Load the config using the utility function
loaded_config = load_configuration(str(config_path))
print(f"Loaded sections: {list(loaded_config.keys())}")
print(f"SQLite section exists: {'SQLite' in loaded_config}")
print(f"Routing section exists: {'Routing' in loaded_config}")

if 'SQLite' in loaded_config:
    print(f"SQLite db_file: {loaded_config['SQLite']['db_file']}")
if 'Routing' in loaded_config:
    print(f"Routing anime_tv_path: {loaded_config['Routing']['anime_tv_path']}") 