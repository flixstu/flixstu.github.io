import os
import hashlib
import zipfile
import re

def generate():
    zips_dir = os.path.dirname(os.path.abspath(__file__))
    addons_xml_path = os.path.join(zips_dir, 'addons.xml')
    md5_path = os.path.join(zips_dir, 'addons.xml.md5')
    
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    
    print("Starting generator...")
    
    directories = [d for d in os.listdir(zips_dir) if os.path.isdir(os.path.join(zips_dir, d))]
    for folder in directories:
        folder_path = os.path.join(zips_dir, folder)
        addon_xml_content = None
        
        # Method 1: Try reading directly from the zip file so we never get it wrong
        zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]
        if zip_files:
            zip_files.sort(reverse=True)
            zip_path = os.path.join(folder_path, zip_files[0])
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    for name in zf.namelist():
                        # We want the main addon.xml from the root folder inside the zip
                        if name.endswith('addon.xml') and name.count('/') <= 1:
                            addon_xml_content = zf.read(name).decode('utf-8')
                            break
            except Exception as e:
                print(f"Error reading zip {zip_path}: {e}")
                
        # Method 2: If no zip or zip failed to read, try reading from unzipped folder
        if not addon_xml_content:
            for root, dirs, files in os.walk(folder_path):
                if 'addon.xml' in files:
                    try:
                        with open(os.path.join(root, 'addon.xml'), 'r', encoding='utf-8') as f:
                            addon_xml_content = f.read()
                        break
                    except Exception as e:
                        print(f"Error reading addon.xml from folder: {e}")
                        
        if addon_xml_content:
            # Remove XML declaration from the individual addon.xml if present
            addon_xml_content = re.sub(r'<\?xml.*?\?>', '', addon_xml_content)
            
            # Find the addon tag block
            match = re.search(r'(<addon.*?</addon>)', addon_xml_content, re.DOTALL | re.IGNORECASE)
            if match:
                addons_xml += match.group(1).strip() + '\n\n'
                print(f"Added: {folder}")
            else:
                print(f"Warning: Could not parse addon.xml properly for {folder}")
        else:
            print(f"Warning: Could not find any addon.xml for {folder}")
            
    addons_xml += '</addons>\n'
    
    # Save addons.xml
    with open(addons_xml_path, 'w', encoding='utf-8') as f:
        f.write(addons_xml)
        
    print("addons.xml has been successfully created.")
        
    # Generate and save MD5
    md5_hash = hashlib.md5(addons_xml.encode('utf-8')).hexdigest()
    with open(md5_path, 'w', encoding='utf-8') as f:
        f.write(md5_hash)
        
    print(f"addons.xml.md5 created with Hash: {md5_hash}")

if __name__ == '__main__':
    generate()
