import json
import locale
import os
import shutil
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests
from tqdm import tqdm


@dataclass
class ModelEntry:
    name: str
    language: str
    size: str
    download_url: str


def get_default_language():
    loc, _ = locale.getdefaultlocale()
    if loc:
        return loc.split("_")[0]
    return "en"

def is_recent_file(file_path: Path) -> bool:
    if not file_path.exists():
        return False   
    current_time = time.time()
    mod_time = file_path.stat().st_mtime
    return (current_time - mod_time) < 24 * 3600  # 24 hours in seconds

class _ModelCache:
    def __init__(self, app_name="aikeyboard"):
        if sys.platform == "win32":
            base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
        self.cache_dir = base / app_name / "models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.models: List[ModelEntry] = []
        self._selected_model: Optional[str] = None
        self.refresh()

    def refresh(self):
        """Fetch and parse the model list from the JSON endpoint."""
        model_list_json = self.cache_dir / "model-list.json"
        if is_recent_file(model_list_json):
            with open(model_list_json) as fi:
                model_list = json.load(fi)
        else:
            try:
                response = requests.get("https://alphacephei.com/vosk/models/model-list.json")
                response.raise_for_status()
                model_list = response.json()
            except requests.RequestException as e:
                print(f"Error fetching model list: {e}")
                return
            with open(model_list_json, 'w') as fo:
                json.dump(model_list, fo, indent=4)

        # if we get here model_list is valid
        self.models.clear()
        for model in model_list:
            name = model.get("name")
            language = model.get("lang")
            size = model.get("type", "unknown")
            download_url = model.get("url")
            obsolete = model.get("obsolete", "false").lower() == 'true'
            if name and language and download_url and not obsolete:
                self.models.append(ModelEntry(name, language, size, download_url))
        # Optional: sort models by language and size
        self.models.sort(key=lambda m: (m.language, m.size))

    def get_languages(self) -> List[str]:
        return sorted({m.language for m in self.models})

    def get_models_for_language(self, lang: str) -> List[ModelEntry]:
        return [m for m in self.models if m.language == lang]

    def get_model_by_name(self, name: str) -> Optional[ModelEntry]:
        for m in self.models:
            if m.name == name:
                return m
        return None

    def selected_model_entry(self) -> Optional[ModelEntry]:
        return self.get_model_by_name(self._selected_model) if self._selected_model else None


    def ensure_model(self) -> str:
        from aikeyboard.config import app_config

        model_name = str(app_config.model)

        # Select from known models
        if not model_name:
            lang = get_default_language()
            models = self.get_models_for_language(lang)
            if not models:
                raise ValueError(f"No default model for language '{lang}'")
            model_name = models[0].name
            model_url = models[0].download_url
        else:
            model = self.get_model_by_name(model_name)
            if model is None:
                raise ValueError(f"Model with name '{model_name}' is not known")
            model_url = model.download_url
            lang = model.language

        model_path = self.cache_dir / lang / model_name
        if model_path.exists():
            return str(model_path)

        # Download and unzip
        lang_dir = self.cache_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        zip_path = lang_dir / f"{model_name}.zip"

        print(f"Downloading {model_name} model...")
        with requests.get(model_url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(zip_path, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=model_name
            ) as pbar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

        print(f"Extracting model to {model_path}...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            tmp_dir = tempfile.mkdtemp(dir=lang_dir)
            zip_ref.extractall(tmp_dir)
            extracted_path = Path(tmp_dir) / model_name
            shutil.move(str(extracted_path), str(model_path))
            shutil.rmtree(tmp_dir)

        zip_path.unlink()
        return str(model_path)

model_cache = _ModelCache()
