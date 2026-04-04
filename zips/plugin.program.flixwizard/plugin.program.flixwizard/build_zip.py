import os
import zipfile
import xml.etree.ElementTree as ET

def get_addon_info():
    tree = ET.parse('addon.xml')
    root = tree.getroot()
    return root.attrib.get('id'), root.attrib.get('version')

def create_zip():
    try:
        addon_id, version = get_addon_info()
    except Exception as e:
        print(f"Error reading addon.xml: {e}")
        return

    zip_filename = f"../{addon_id}-{version}.zip"
    print(f"Creating {zip_filename}...")

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Ignore hidden/system directories
            if any(exclude in root for exclude in ['.git', '__pycache__', '.idea', '.vscode', '.gemini']):
                continue
                
            for file in files:
                # Ignore the zip script and any zip files
                if file == 'build_zip.py' or file.endswith('.zip'):
                    continue
                
                file_path = os.path.join(root, file)
                # Ensure the files are packed inside a folder named after the addon_id
                arcname = os.path.join(addon_id, os.path.relpath(file_path, '.'))
                zipf.write(file_path, arcname)

    print(f"Done! Created {zip_filename} in the folder above.")

if __name__ == '__main__':
    create_zip()
