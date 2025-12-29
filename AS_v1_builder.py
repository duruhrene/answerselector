import PyInstaller.__main__
import shutil
from pathlib import Path

def build():
    # 1. Clean previous build
    if Path("dist").exists():
        shutil.rmtree("dist")
    if Path("build").exists():
        shutil.rmtree("build")

    # 2. Run PyInstaller
    PyInstaller.__main__.run([
        'main.py',
        '--name=AnswerSelector',
        '--noconsole',  # Hide console window
        '--onedir',     # One Folder mode (Not single file)
        '--clean',
        '--exclude-module=tkinter',
        '--exclude-module=pandas',
        '--exclude-module=PIL',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=unittest',
        '--exclude-module=openpyxl',
        # Exclude large data folders from the bundle (they will be external)
    ])

    # 3. Post-build data setup (Verification/Copying)
    dist_dir = Path("dist")
    output_dir = dist_dir / "AnswerSelector" # One-folder output directory
    exe_path = output_dir / "AnswerSelector.exe"
    
    # Create external data folders inside the output directory
    (output_dir / "database").mkdir(exist_ok=True)
    model_out_dir = output_dir / "model"
    model_out_dir.mkdir(exist_ok=True)

    # Copy about_model_file.txt if it exists
    src_file = Path("model/about_model_file.txt")
    if src_file.exists():
        shutil.copy2(src_file, model_out_dir)
        print(f"Copied {src_file.name} to {model_out_dir}")
        
    # Copy License file
    license_file = Path("THIRDPARTY_LICENSE.txt")
    if license_file.exists():
        shutil.copy2(license_file, output_dir)
        print(f"Copied {license_file.name} to {output_dir}")

    # Copy Copyright file
    copyright_file = Path("LICENSE")
    if copyright_file.exists():
        shutil.copy2(copyright_file, output_dir)
        print(f"Copied {copyright_file.name} to {output_dir}")
    
    print("\n[Build Complete]")
    print(f"Output Directory: {output_dir}")
    print(f"Executable: {exe_path}")
    print("Don't forget to populate 'database' and 'model' folders in the output directory!")

if __name__ == "__main__":
    build()
