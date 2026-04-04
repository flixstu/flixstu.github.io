import os
import hashlib
import zipfile
import xml.etree.ElementTree as ET

def get_addon_xml_from_zip(zip_path):
    """Extract addon.xml content from a zip file."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                # Only the top-level addon.xml (one folder deep max)
                parts = name.split('/')
                if parts[-1] == 'addon.xml' and len(parts) == 2:
                    return zf.read(name).decode('utf-8-sig')
    except Exception as e:
        print(f"  Error reading zip {zip_path}: {e}")
    return None

def get_addon_xml_from_folder(folder_path):
    """Find and read addon.xml from an unzipped addon folder."""
    for root, dirs, files in os.walk(folder_path):
        if 'addon.xml' in files:
            try:
                with open(os.path.join(root, 'addon.xml'), 'r', encoding='utf-8-sig') as f:
                    return f.read()
            except Exception as e:
                print(f"  Error reading addon.xml: {e}")
    return None

def parse_addon_element(xml_content):
    """Parse XML content and return the addon element as a clean ET element."""
    # Normalize line endings first
    xml_content = xml_content.replace('\r\n', '\n').replace('\r', '\n')
    
    try:
        # Parse the whole document
        root = ET.fromstring(xml_content)
        
        # Handle both cases: root IS the addon, or root contains addons
        if root.tag == 'addon':
            return root
        elif root.tag == 'addons':
            addon = root.find('addon')
            if addon is not None:
                return addon
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
    return None

def indent(elem, level=0):
    """Add pretty-print indentation to an XML element tree."""
    pad = '\n' + '    ' * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + '    '
        if not elem.tail or not elem.tail.strip():
            elem.tail = pad
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = pad
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = pad
    if not level:
        elem.tail = '\n'

def generate():
    zips_dir = os.path.dirname(os.path.abspath(__file__))
    addons_xml_path = os.path.join(zips_dir, 'addons.xml')
    md5_path = os.path.join(zips_dir, 'addons.xml.md5')

    print("Starting generator...")

    root = ET.Element('addons')
    root.text = '\n'

    directories = sorted([
        d for d in os.listdir(zips_dir)
        if os.path.isdir(os.path.join(zips_dir, d))
    ])

    for folder in directories:
        folder_path = os.path.join(zips_dir, folder)
        xml_content = None

        # Try reading from zip first
        zip_files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith('.zip')],
            reverse=True
        )
        if zip_files:
            xml_content = get_addon_xml_from_zip(os.path.join(folder_path, zip_files[0]))

        # Fallback: read from unzipped folder
        if not xml_content:
            xml_content = get_addon_xml_from_folder(folder_path)

        if not xml_content:
            print(f"  WARNING: No addon.xml found for {folder}")
            continue

        addon_elem = parse_addon_element(xml_content)
        if addon_elem is None:
            print(f"  WARNING: Could not parse addon.xml for {folder}")
            continue

        # Clean up any \r that snuck through in text/tail
        for elem in addon_elem.iter():
            if elem.text:
                elem.text = elem.text.replace('\r', '')
            if elem.tail:
                elem.tail = elem.tail.replace('\r', '')

        indent(addon_elem, level=1)
        addon_elem.tail = '\n'
        root.append(addon_elem)
        print(f"  Added: {folder} ({addon_elem.get('id')})")

    # Serialize to clean UTF-8 XML string
    ET.indent(root, space='    ')
    xml_bytes = ET.tostring(root, encoding='unicode', xml_declaration=False)
    
    final_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_bytes + '\n'
    
    # Make absolutely sure no \r\r\n exists
    final_xml = final_xml.replace('\r\n', '\n').replace('\r', '\n')

    with open(addons_xml_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(final_xml)

    print(f"\naddons.xml created successfully ({len(final_xml)} bytes)")

    # MD5 must match the exact bytes Kodi will download (UTF-8, no BOM)
    md5_hash = hashlib.md5(final_xml.encode('utf-8')).hexdigest()
    with open(md5_path, 'w', encoding='utf-8', newline='') as f:
        f.write(md5_hash)

    print(f"addons.xml.md5: {md5_hash}")

if __name__ == '__main__':
    generate()
