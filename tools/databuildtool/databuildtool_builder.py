import PyInstaller.__main__
import shutil
from pathlib import Path

import os

def build():
    # 0. Set working directory to script location
    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)

    # 1. Clean previous build
    if Path("dist").exists():
        shutil.rmtree("dist")
    if Path("build").exists():
        shutil.rmtree("build")

    # 2. Run PyInstaller
    PyInstaller.__main__.run([
        'databuildtool.py',
        '--name=DataBuildTool',
        '--noconsole',
        '--onefile',
        '--clean',
        '--exclude-module=pandas',
        '--exclude-module=wx',
        '--exclude-module=PIL',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        # Note: onnxruntime, numpy, pandas will be included automatically
    ])

    print("\n[Build Complete]")
    print("Executable: dist/DataBuilder/DataBuildTool.exe")

if __name__ == "__main__":
    build()
