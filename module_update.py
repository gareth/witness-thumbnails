import os
import subprocess
import sys
from importlib import util

local_dir = os.path.dirname(__file__)
file = os.path.join(local_dir, "requirements.txt")

required = set()

with open(file) as f:
    for line in f.readlines():
        line = line.strip()

        if line == "Pillow":
            required.add("PIL")
        else:
            required.add(line)

missing = {pkg for pkg in required if util.find_spec(pkg) is None}

if missing:
    subprocess.call([sys.executable, "-m", "pip", "install", "-r", file, "--upgrade"])
