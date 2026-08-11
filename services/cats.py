from pathlib import Path
import random

def random_cat():
    folder=Path(__file__).resolve().parent.parent/"cats"
    files=[p for p in folder.iterdir() if p.suffix.lower() in {".jpg",".jpeg",".png",".webp"}]
    return random.choice(files) if files else None
