import zipfile
import os

addon_xml = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<addon id="repository.flixstudioss" name="[B][COLOR lightblue]Flix[/B][COLOR white]Studioss Repository[/COLOR]" version="1.0.0" provider-name="FlixStudioss">\n'
    '    <requires>\n'
    '        <import addon="xbmc.python" version="3.0.0"/>\n'
    '    </requires>\n'
    '    <extension point="xbmc.addon.repository" name="FlixStudioss Repository">\n'
    '        <dir>\n'
    '            <info compressed="false">https://raw.githubusercontent.com/flixstu/flixstu.github.io/main/zips/addons.xml</info>\n'
    '            <checksum>https://raw.githubusercontent.com/flixstu/flixstu.github.io/main/zips/addons.xml.md5</checksum>\n'
    '            <datadir zip="true">https://raw.githubusercontent.com/flixstu/flixstu.github.io/main/zips/</datadir>\n'
    '        </dir>\n'
    '    </extension>\n'
    '    <extension point="xbmc.addon.metadata">\n'
    '        <summary lang="en">Official FlixStudioss Kodi Repository</summary>\n'
    '        <description lang="en">Official FlixStudioss Repository for all our Kodi Addons.</description>\n'
    '        <platform>all</platform>\n'
    '        <assets>\n'
    '            <icon>icon.png</icon>\n'
    '        </assets>\n'
    '    </extension>\n'
    '</addon>\n'
)

# Write clean addon.xml to disk
addon_xml_path = r'repository.flixstudioss\repository.flixstudioss\addon.xml'
with open(addon_xml_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(addon_xml)
print('addon.xml written cleanly')

# Rebuild zip with clean content written directly (no reading from disk)
icon_path = r'repository.flixstudioss\repository.flixstudioss\icon.png'
zip_out = r'repository.flixstudioss\repository.flixstudioss-1.0.0.zip'

with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('repository.flixstudioss/addon.xml', addon_xml.encode('utf-8'))
    if os.path.exists(icon_path):
        zf.write(icon_path, 'repository.flixstudioss/icon.png')
        print('icon.png added')

print('Zip rebuilt cleanly')

# Verify
with zipfile.ZipFile(zip_out, 'r') as zf:
    content = zf.read('repository.flixstudioss/addon.xml')
    print('\\r\\r\\n count:', content.count(b'\r\r\n'))
    print('\\r\\n count:', content.count(b'\r\n'))
    print('OK - clean newlines only:', content.count(b'\n'))
