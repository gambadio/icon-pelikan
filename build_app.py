#!/usr/bin/env python3
"""
Build script for creating a macOS app bundle of Icon Pelikan.
"""

import subprocess
import sys
from pathlib import Path
import shutil

def build_app():
    """Build the macOS app bundle using PyInstaller."""
    
    # Get the current directory
    project_dir = Path(__file__).parent
    
    # Clean up any previous builds
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"
    
    if dist_dir.exists():
        print("Cleaning up previous dist directory...")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print("Cleaning up previous build directory...")
        shutil.rmtree(build_dir)
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=Icon Pelikan",           # App name
        "--windowed",                    # No console window
        "--onedir",                      # Create a directory bundle
        "--icon=assets/icon_pelikan.icns",  # App icon
        "--add-data=assets:assets",      # Include assets folder
        "--osx-bundle-identifier=com.pelikanco.iconpelikan",  # Bundle identifier
        "--clean",                       # Clean cache and remove temporary files
        "main.py"                        # Entry point
    ]
    
    print("Building Icon Pelikan.app...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, cwd=project_dir, check=True, capture_output=True, text=True)
        print("Build successful!")
        
        app_path = dist_dir / "Icon Pelikan.app"
        if app_path.exists():
            print(f"\nApp bundle created at: {app_path}")
            print(f"You can run it with: open '{app_path}'")
            
            # Show the app size
            size_cmd = ["du", "-sh", str(app_path)]
            size_result = subprocess.run(size_cmd, capture_output=True, text=True)
            if size_result.returncode == 0:
                print(f"App bundle size: {size_result.stdout.strip().split()[0]}")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    
    return True

if __name__ == "__main__":
    success = build_app()
    sys.exit(0 if success else 1)
