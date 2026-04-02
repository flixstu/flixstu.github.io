import os
import zipfile
import xml.etree.ElementTree as ET
import sys

def zip_addon(addon_dir=None):
    # If no directory is provided, search the current directory for folders containing addon.xml
    if not addon_dir:
        for item in os.listdir("."):
            if os.path.isdir(item) and os.path.exists(os.path.join(item, "addon.xml")):
                addon_dir = item
                break
    
    if not addon_dir or not os.path.isdir(addon_dir):
        print("Error: Could not find a folder with addon.xml in it.")
        return

    addon_xml_path = os.path.join(addon_dir, "addon.xml")
    if not os.path.exists(addon_xml_path):
        print(f"Error: {addon_xml_path} not found.")
        return

    try:
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()
        addon_id = root.attrib.get('id')
        version = root.attrib.get('version')
    except Exception as e:
        print(f"Error parsing addon.xml: {e}")
        return

    if not addon_id or not version:
        print("Error: addon.xml is missing 'id' or 'version' attribute.")
        return

    zip_filename = f"{addon_id}-{version}.zip"
    print(f"Zipping '{addon_dir}' into '{zip_filename}'...")

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root_path, dirs, files in os.walk(addon_dir):
            for file in files:
                # Common ignores for Kodi addons
                if file.endswith(('.pyc', '.pyo', '.git', '.DS_Store', 'Thumbs.db')):
                    continue
                if any(x.startswith('.') for x in root_path.split(os.sep)):
                    continue

                abs_path = os.path.join(root_path, file)
                # Keep the same path structure inside the zip
                arcname = os.path.relpath(abs_path, os.path.dirname(addon_dir) or ".")
                zipf.write(abs_path, arcname)

    print(f"Successfully created: {zip_filename}")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else None
    zip_addon(target_dir)
