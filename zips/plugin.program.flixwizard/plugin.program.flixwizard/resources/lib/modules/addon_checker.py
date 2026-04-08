import xbmc
import xbmcgui
import xbmcaddon
import urllib.request
from uservar import build_version_url
from .addonvar import setting, setting_set, addon_id, addon_name

# Mapping of keys -> add-ons
ADDON_MAPPING = {
    "aguiavavoo": {"id": "plugin.video.aguiavavoo", "name": "Aguiavavoo"},
    "elementum": {"id": "plugin.video.elementum", "name": "Elementum"},
    "homelander": {"id": "plugin.video.homelander", "name": "Homelander"},
    "playlistbee": {"id": "plugin.video.playlistbee", "name": "PlaylistBee"},
    "scrubsv2": {"id": "plugin.video.scrubsv2", "name": "Scrubs V2"},
    "sporthdme": {"id": "plugin.video.sporthdme", "name": "SportsHDME"},
    "thecrew": {"id": "plugin.video.thecrew", "name": "The Crew"},
    "umbrella": {"id": "plugin.video.umbrella", "name": "Umbrella"},
    "vavooto": {"id": "plugin.video.vavooto", "name": "Vavoo.to"},
    "daddylive": {"id": "plugin.video.daddylive", "name": "DaddyLive"},
    "amkoiptv": {"id": "plugin.video.amko", "name": "AmkoIptv"},
    "theloop": {"id": "plugin.video.the-loop", "name": "TheLoop"},
    "apexsports": {"id": "plugin.video.apex_sports", "name": "ApexSports"},
    "madtitan": {"id": "plugin.video.madtitansports_apple", "name": "MadTitanSports"},
    "fenlite": {"id": "plugin.video.fenlight", "name": "FenLight"},
    "livetvser": {"id": "plugin.video.livetvSerbia", "name": "LiveTVSerbia"}
}

def check_addons():
    """Checks for missing addons or available updates from the mapping."""
    # Trigger a repository check to ensure Kodi sees new versions
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(2000) # Give it a moment to start
    
    for key, data in ADDON_MAPPING.items():
        addon_id_to_check = data["id"]
        addon_name_to_check = data["name"]
        
        # Only trigger update if the addon is already installed and an update is detected
        if xbmc.getCondVisibility(f"System.HasUpdate({addon_id_to_check})"):
            xbmcgui.Dialog().notification("FlixWizard", f"Auto-updating {addon_name_to_check}...")
            xbmc.executebuiltin(f"InstallAddon({addon_id_to_check})")

def check_build_update():
    """Checks for build update from remote text file."""
    if build_version_url in ('', 'https://flixstu.github.io/zips/version.txt'):
        return

    try:
        req = urllib.request.Request(build_version_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8').strip()
            
        # Handle formats like "Update v2.0", "v2.0", or just "2.0"
        remote_version = content.lower().replace('update', '').replace('v', '').strip()
        current_version = setting('buildversion').lower().replace('v', '').strip() or "1.0"
        
        # Simple string comparison or float comparison could work here
        # but string comparison "2.0" > "1.1" is generally okay for simple versioning
        if remote_version > current_version:
            import_wizard = xbmcgui.Dialog().yesno(
                "Update Available",
                f"A new build version {content} is available (Current: {setting('buildversion')}).\n\nWould you like to open {addon_name} to update?"
            )
            if import_wizard:
                xbmc.executebuiltin(f"RunAddon({addon_id})")
    except Exception as e:
        xbmc.log(f"[{addon_name}] Error checking build version: {str(e)}", xbmc.LOGERROR)
