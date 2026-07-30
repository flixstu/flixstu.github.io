import zipfile
import hashlib
import os
import xml.etree.ElementTree as ET

BASE_URL = "https://flixstu.github.io/zips"

REPO_ID = "repository.flixstudioss"
REPO_NAME = "FlixStudioss Repository"
REPO_VERSION = "1.0.0"
REPO_PROVIDER = "FlixStudioss"

REPO_ADDON_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{repo_id}" name="{repo_name}" version="{version}" provider-name="{provider}">
    <requires>
        <import addon="xbmc.python" version="3.0.0"/>
    </requires>
    <extension point="xbmc.addon.repository" name="{repo_name}">
        <dir>
            <info>{base_url}/addons.xml</info>
            <checksum>{base_url}/addons.xml.md5</checksum>
            <datadir zip="true">{base_url}/</datadir>
            <hashes>false</hashes>
        </dir>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en">Official FlixStudioss Kodi Repository</summary>
        <description lang="en">Official FlixStudioss Repository for all our Kodi Addons.</description>
        <platform>all</platform>
        <assets>
            <icon>icon.jpg</icon>
        </assets>
    </extension>
</addon>
""".format(
    repo_id=REPO_ID,
    repo_name=REPO_NAME,
    version=REPO_VERSION,
    provider=REPO_PROVIDER,
    base_url=BASE_URL,
)

ADDONS_XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
ADDONS_XML_FOOTER = '</addons>\n'

ZIPS_DIR = os.path.dirname(os.path.abspath(__file__))


def extract_addon_xml_from_zip(zip_path, addon_id):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('/addon.xml'):
                raw = zf.read(name)
                return raw.decode('utf-8')
    return None


def strip_xml_declaration(xml_str):
    lines = xml_str.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('<?xml'):
            continue
        result.append(line)
    return '\n'.join(result)


def normalize_addon_entry(xml_str):
    root = ET.fromstring(xml_str)
    lines = []
    lines.append('    <addon id="{id}" name="{name}" version="{version}" provider-name="{provider}">'.format(
        id=root.attrib['id'],
        name=root.attrib['name'],
        version=root.attrib['version'],
        provider=root.attrib.get('provider-name', ''),
    ))

    for child in root:
        lines.append(xml_stringify(child, indent=2))

    lines.append('    </addon>')
    return '\n'.join(lines)


def xml_stringify(elem, indent=0):
    pad = ' ' * indent
    tag = elem.tag
    attribs = ''
    for k, v in elem.attrib.items():
        attribs += ' {}="{}"'.format(k, v)

    children = list(elem)
    if not children and elem.text and elem.text.strip():
        return '{}<{}{}>{}</{}>'.format(pad, tag, attribs, elem.text.strip(), tag)
    elif not children and (elem.text is None or elem.text.strip() == ''):
        return '{}<{}{}/>'.format(pad, tag, attribs)
    else:
        lines = ['{}<{}{}>'.format(pad, tag, attribs)]
        if elem.text and elem.text.strip():
            lines.append('{}    {}'.format(pad, elem.text.strip()))
        for child in elem:
            lines.append(xml_stringify(child, indent + 4))
        if elem.tail and elem.tail.strip():
            lines.append('{}    {}'.format(pad, elem.tail.strip()))
        lines.append('{}</{}>'.format(pad, tag))
        return '\n'.join(lines)


def main():
    addons = []

    addon_dirs = {
        'plugin.program.flixwizard': 'plugin.program.flixwizard',
        'script.module.resolveurl': 'script.module.resolveurl',
    }

    for addon_id, dirname in sorted(addon_dirs.items()):
        zip_files = [f for f in os.listdir(os.path.join(ZIPS_DIR, dirname)) if f.endswith('.zip')]
        if not zip_files:
            print('WARNING: No zip found for {}'.format(addon_id))
            continue
        zip_path = os.path.join(ZIPS_DIR, dirname, zip_files[0])
        print('Reading {} from {}'.format(addon_id, zip_files[0]))
        xml_str = extract_addon_xml_from_zip(zip_path, addon_id)
        if xml_str:
            addons.append(xml_str)
        else:
            print('WARNING: Could not extract addon.xml from {}'.format(zip_path))

    repo_xml_path = os.path.join(ZIPS_DIR, REPO_ID, REPO_ID, 'addon.xml')
    os.makedirs(os.path.dirname(repo_xml_path), exist_ok=True)
    with open(repo_xml_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(REPO_ADDON_XML)
    print('Written {}'.format(repo_xml_path))

    addons_xml_path = os.path.join(ZIPS_DIR, 'addons.xml')
    with open(addons_xml_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(ADDONS_XML_HEADER)
        for xml_str in addons:
            f.write(normalize_addon_entry(xml_str))
            f.write('\n')
        f.write(normalize_addon_entry(REPO_ADDON_XML))
        f.write('\n')
        f.write(ADDONS_XML_FOOTER)
    print('Written {}'.format(addons_xml_path))

    with open(addons_xml_path, 'rb') as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    md5_path = os.path.join(ZIPS_DIR, 'addons.xml.md5')
    with open(md5_path, 'w', newline='\n') as f:
        f.write(md5)
    print('Written {} ({})'.format(md5_path, md5))

    icon_path = os.path.join(ZIPS_DIR, REPO_ID, REPO_ID, 'icon.jpg')
    zip_out = os.path.join(ZIPS_DIR, REPO_ID, '{}-{}.zip'.format(REPO_ID, REPO_VERSION))
    with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('{}/addon.xml'.format(REPO_ID), REPO_ADDON_XML.encode('utf-8'))
        if os.path.exists(icon_path):
            zf.write(icon_path, '{}/icon.jpg'.format(REPO_ID))
            print('icon.jpg added to zip')
    print('Written {}'.format(zip_out))

    with zipfile.ZipFile(zip_out, 'r') as zf:
        print('\nZip contents:')
        for info in zf.infolist():
            print('  {} ({} bytes)'.format(info.filename, info.file_size))
        content = zf.read('{}/addon.xml'.format(REPO_ID))
        print('\nNewline check:')
        print('  \\r\\r\\n: {}'.format(content.count(b'\r\r\n')))
        print('  \\r\\n: {}'.format(content.count(b'\r\n')))
        print('  \\n: {}'.format(content.count(b'\n')))

    print('\nDone!')


if __name__ == '__main__':
    main()
