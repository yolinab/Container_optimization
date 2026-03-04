# Shipping ContainerOptimizer to Work Windows Computers

This guide covers building the app on Windows and deploying it to admin-protected work machines.

---

## Part 1 — Build the exe (your machine, one time per update)

### Prerequisites
Python 3.10+ and your venv must be set up. Run these once:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

### Build

```bat
.venv\Scripts\activate
build_windows.bat
```

Output: `dist\ContainerOptimizer\` — this is what you ship.

### Zip it

```bat
powershell Compress-Archive -Path dist\ContainerOptimizer -DestinationPath ContainerOptimizer.zip
```

Or right-click `dist\ContainerOptimizer` in Explorer → Send to → Compressed (zipped) folder.

---

## Part 2 — Install on a colleague's admin-protected work computer

### Key point
The app needs **no admin rights to run**. The only thing that might need admin is the one-time VC++ runtime install — and on most work machines it's already there.

---

### Step 1 — Transfer the zip

Options (pick whichever your company allows):

- Email the zip (if under attachment size limit, usually 25 MB)
- Upload to Teams / SharePoint / OneDrive and share the link
- USB drive
- Shared network drive: `copy ContainerOptimizer.zip \\SERVER\Share\`

---

### Step 2 — On the colleague's machine: extract

Have them open **PowerShell** (no admin needed) and run:

```powershell
# Change the path to wherever they saved the zip
Expand-Archive -Path "$env:USERPROFILE\Downloads\ContainerOptimizer.zip" -DestinationPath "$env:USERPROFILE\Desktop\ContainerOptimizer"
```

Or just right-click the zip → Extract All → choose Desktop.

---

### Step 3 — Run the app

Double-click `ContainerOptimizer.exe` inside the extracted folder.

If Windows SmartScreen blocks it (blue warning dialog):
- Click **More info**
- Click **Run anyway**

This is normal for apps not yet digitally signed. It is a one-time prompt.

---

### Step 4 — If the app crashes immediately (VC++ runtime missing)

A dialog will appear with the download link. If they cannot download from the internet, you can pre-download the installer and send it alongside the zip:

```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

**If they have admin rights:** just double-click `vc_redist.x64.exe` and install.

**If they do NOT have admin rights:** ask IT to push the VC++ runtime remotely, or ask them to run:

```powershell
# IT can deploy silently with:
vc_redist.x64.exe /install /quiet /norestart
```

On most office machines (anything with Office, Chrome, or Teams installed) the VC++ runtime is already present and this step is not needed.

---

## Part 3 — Updating (bug fixes)

### You push a fix, they get it in under 2 minutes

**Your side:**
1. Fix the code
2. Rebuild:
   ```bat
   .venv\Scripts\activate
   build_windows.bat
   ```
3. Re-zip:
   ```bat
   powershell Compress-Archive -Path dist\ContainerOptimizer -DestinationPath ContainerOptimizer.zip -Force
   ```
4. Put the new zip in the shared location (Teams, network drive, email)

**Their side:**
1. Delete the old `ContainerOptimizer` folder on their Desktop (or wherever they put it)
2. Extract the new zip
3. Run `ContainerOptimizer.exe`

No reinstall, no admin rights, no Python, nothing else.

---

## Failsafes

### `build_windows.bat` fails with "pyinstaller not found"
```bat
.venv\Scripts\activate
pip install pyinstaller
build_windows.bat
```

### `build_windows.bat` fails with "No module named X"
```bat
.venv\Scripts\activate
pip install -r requirements.txt
build_windows.bat
```

### App opens but crashes when loading a file
Check that `optimizer_config.json` is present in the same folder as `ContainerOptimizer.exe`. The build script copies it automatically, but if it got lost:
```bat
copy optimizer_config.json dist\ContainerOptimizer\optimizer_config.json
```

### SmartScreen blocks the exe and there is no "Run anyway" option
This means the machine's IT policy blocks unsigned executables. Options:
1. Ask IT to whitelist the folder (e.g. `C:\Tools\ContainerOptimizer\`)
2. Get a code-signing certificate (~$100/year) and sign the exe:
   ```bat
   signtool sign /fd SHA256 /t http://timestamp.digicert.com /f certificate.pfx /p PASSWORD dist\ContainerOptimizer\ContainerOptimizer.exe
   ```
3. Run directly from a network share that IT has already whitelisted

### PowerShell says "execution of scripts is disabled"
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
If that is blocked too, use Command Prompt instead of PowerShell for everything.

### Expand-Archive not available (very old Windows / PowerShell 2)
```bat
# Use built-in tar (Windows 10 1803+):
tar -xf ContainerOptimizer.zip -C %USERPROFILE%\Desktop\
```

### The app runs but outputs folder is not opening / report not found
The app writes outputs next to the exe by default. Make sure the folder is not in a read-only location (e.g. `Program Files`). Desktop or Documents always works.

---

## Summary

| Step | Who | Admin needed? |
|------|-----|---------------|
| Build exe | You | No |
| Transfer zip | You | No |
| Extract zip | Colleague | No |
| Run exe | Colleague | No |
| SmartScreen prompt | Colleague | No (just click "Run anyway") |
| VC++ runtime (if missing) | IT or colleague | Yes (one-time) |
| Future updates | Just re-extract new zip | No |
