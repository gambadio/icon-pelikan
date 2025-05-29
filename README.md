# Icon Pelikan

A minimal Mac-style icon generator with a brutalist grainy UI.

## Setup (dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Packaging for macOS

```bash
pip install pyinstaller
pyinstaller \
  --noconsole \
  --windowed \
  --name "Icon Pelikan" \
  --icon assets/icon_pelikan.icns \
  main.py
```

After PyInstaller finishes you’ll find `dist/Icon Pelikan.app` ready to drag into `/Applications`.

## Generating icon_pelikan.icns

If you only have the PNG:

```bash
# inside the repo root
iconutil -c icns IconPelikan.iconset     # produced via the app’s “Save .icns”
mv IconPelikan.icns assets/icon_pelikan.icns
```

## Smart features
	•	Drag-and-drop image loading
	•	Live sliders: canvas size / scale / radius
	•	Circle or rounded-square mode
	•	Optional solid background tint
	•	Automatic Apple .iconset + .icns export (macOS iconutil)
	•	Grainy radial gradient background rendered at runtime
	•	Dark-theme widgets with custom flat buttons

---

## 3 · What was fixed / improved

* **Layout bug resolved** – controls now sit in a dedicated column that never clips, thanks to Qt layouts.  
* **Modern aesthetic** – custom painter gives the noisy dark gradient; widgets carry flat brutalist styles. Qt lets us combine gradients & textures easily   
* **Smart extras** – drag-and-drop, colour picker, .iconset → .icns conversion, DPI-aware previews, About box.  
* **Packaging-ready** – the repo ships with requirements.txt + PyInstaller recipe; just add your toucan PNG to `assets/` as `icon_pelikan.png`.  

Enjoy shipping **Icon Pelikan**!