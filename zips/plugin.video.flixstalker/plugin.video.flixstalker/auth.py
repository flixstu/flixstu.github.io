
from __future__ import absolute_import, division, unicode_literals
import json, time, requests, os
from types import SimpleNamespace
from urllib.parse import urljoin, quote_plus
import xbmcvfs
import globals as G
from logger import Logger

STALKER_ENDPOINTS = [
    '/stalker_portal/c/portal.php',
    '/portal.php',
    '/stalker_portal/server/load.php',
    '/server/load.php',
    '/c/load.php',
    '/stalker_portal/load.php',
    '/stalker_portal/api.php',
    '/api.php',
    '/stalker_portal/server/api.php',
    '/portalstb/load.php',
    '/stalker_portal/info.php',
    '/stb_info.php',
    '/stalker_portal/c/',
    '/c/',
    '/stalker_portal/',
    '/portal/',
    '/stalker_portal/index.php',
    '/index.php',
    '/auth/login', 
    '/stalker_portal/auth/login', 
    '/portal/api/',
    '/stalker_portal/main/',
    '/stalker_portal/main/index.html',
]

# ----------------------------
# CACHE FUNKCIJE
# ----------------------------
def _get_token_cache_file_path():
    return os.path.join(G.ADDON_DATA_PATH, 'stalker_token.json')

def _load_token_from_cache(portal_url_to_check, mac_address_to_check):
    path = _get_token_cache_file_path()
    if not xbmcvfs.exists(path):
        return None
    try:
        with xbmcvfs.File(path) as f:
            data = json.load(f)
        if (data.get("portal_url") == portal_url_to_check and
            data.get("mac_address") == mac_address_to_check and
            data.get("token")):
            Logger.debug(f"Token found in cache for {portal_url_to_check}/{mac_address_to_check}")
            return data["token"]
    except Exception as e:
        Logger.error(f"Token cache load error: {e}")
    return None

def _save_token_to_cache(portal_url, mac, token, full_api_url=None):
    path = _get_token_cache_file_path()
    try:
        if not xbmcvfs.exists(G.ADDON_DATA_PATH):
            xbmcvfs.mkdirs(G.ADDON_DATA_PATH)
        with xbmcvfs.File(path, "w") as f:
            json.dump({
                "portal_url": portal_url,
                "mac_address": mac,
                "token": token,
                "full_api_url": full_api_url
            }, f)
        Logger.debug(f"Token saved to cache for {portal_url}/{mac}")
    except Exception as e:
        Logger.error(f"Token cache save error: {e}")

def _clear_token_cache():
    path = _get_token_cache_file_path()
    try:
        if xbmcvfs.exists(path):
            xbmcvfs.delete(path)
            Logger.debug("Token cache cleared")
    except Exception as e:
        Logger.error(f"Token cache clear error: {e}")

# ----------------------------
# POMOĆNE
# ----------------------------
def _looks_like_valid_response(r):
    if not r: return False
    try:
        j = r.json()
        if isinstance(j, dict) and 'js' in j:
            js = j['js']
            if js.get('token') or js.get('status') == 'OK' or js.get('id') is not None:
                return True
    except Exception:
        pass
    txt = r.text.lower() if hasattr(r, "text") else ""
    for word in ("token", "handshake", "portal", "stalker", "profile"):
        if word in txt:
            return True
    return False

def detect_stalker_endpoint(base_url, mac, timeout=None):
    timeout = timeout or getattr(G, "REQUEST_TIMEOUT", 15)
    if not base_url.endswith("/"):
        base_url += "/"

    Logger.info(f"🔍 Pokrećem detekciju endpointa za {base_url} (timeout={timeout})")

    macs = [mac, mac.upper(), mac.lower()]
    headers = {
        'User-Agent': getattr(G, "USER_AGENT_SETTING", "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp"),
        'X-User-Agent': getattr(G, "DEFAULT_STB_TYPE", "MAG250"),
        'Referer': base_url,
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }

    for path in STALKER_ENDPOINTS:
        url = urljoin(base_url, path.lstrip("/"))
        for m in macs:
            params = {'type': 'stb', 'action': 'handshake', 'token': '', 'mac': m}
            try:
                r = requests.get(url, params=params, headers=headers, cookies={'mac': m}, timeout=timeout)
                Logger.debug(f"Testing endpoint {r.url} -> status {r.status_code}")
                if 200 <= r.status_code < 400 and _looks_like_valid_response(r):
                    Logger.info(f"✅ Pronađen validan endpoint: {url}")
                    return url
            except Exception as e:
                Logger.debug(f"❌ {url} nije validan ({e})")
            time.sleep(0.1)

    Logger.error("❌ Nije pronađen nijedan validan Stalker endpoint.")
    return None
# ---------------------------------
# HANDSHAKE I GET_PROFILE
# ---------------------------------
def _perform_handshake():
    if not getattr(G.active_portal, "full_api_url", None):
        Logger.error("Handshake: full_api_url not set.")
        return None

    params = {'type': 'stb', 'action': 'handshake', 'token': '', 'mac': G.active_portal.mac_address}
    headers = {
        'User-Agent': getattr(G.active_portal, 'user_agent', getattr(G, "USER_AGENT_SETTING", "Mozilla/5.0")),
        'X-User-Agent': getattr(G.active_portal, 'stb_type', getattr(G, "DEFAULT_STB_TYPE", "MAG250")),
        'Referer': getattr(G.active_portal, 'portal_url', '')
    }
    cookies = {'mac': G.active_portal.mac_address}

    try:
        r = requests.get(G.active_portal.full_api_url, params=params, headers=headers, cookies=cookies, timeout=getattr(G, "REQUEST_TIMEOUT", 15))
        Logger.debug(f"Handshake URL: {r.url}")
        r.raise_for_status()
        data = r.json()
        if data.get("js") and data["js"].get("token"):
            Logger.info(f"Handshake OK for {G.active_portal.mac_address}")
            return data["js"]["token"]
        else:
            Logger.error(f"Handshake fail: {data}")
            return None
    except Exception as e:
        Logger.error(f"Handshake error: {e}")
        return None


def _get_profile_and_refresh_token(current_token):
    if not getattr(G.active_portal, "full_api_url", None):
        Logger.error("GetProfile: full_api_url not set.")
        return None

    ver_str = 'ImageDescription: 0.2.18-r23-pub-254; PORTAL version: 5.1.1; JS API'
    params = {
        'type': 'stb', 'action': 'get_profile', 'hd': '1',
        'ver': quote_plus(ver_str), 'num_banks': '1',
        'stb_type': G.active_portal.stb_type, 'image_version': G.active_portal.image_version,
        'video_out': 'hdmi', 'hw_version': G.active_portal.hw_version,
        'mac': G.active_portal.mac_address, 'serial_number': G.active_portal.serial_number,
        'device_id': G.active_portal.device_id, 'device_id2': G.active_portal.device_id2,
        'signature': G.active_portal.signature, 'metrics': '', 'auth_second_step': '0'
    }

    headers = {
        'User-Agent': G.active_portal.user_agent, 'X-User-Agent': G.active_portal.stb_type,
        'Referer': G.active_portal.portal_url, 'Authorization': f'Bearer {current_token}'
    }

    try:
        r = requests.get(G.active_portal.full_api_url, params=params, headers=headers, cookies={'mac': G.active_portal.mac_address}, timeout=getattr(G, "REQUEST_TIMEOUT", 15))
        Logger.debug(f"GetProfile URL: {r.url}")
        r.raise_for_status()
        data = r.json()
        if data.get("js") and (data["js"].get("id") or data["js"].get("token") or data["js"].get("status") == "OK"):
            Logger.info(f"GetProfile OK for {G.active_portal.mac_address}")
            return data["js"].get("token", current_token)
    except Exception as e:
        Logger.error(f"GetProfile error: {e}")
    return None


# ---------------------------------
# AUTENTIFIKACIJA (GLAVNA)
# ---------------------------------
def authenticate_mac(p_url, mac, dev_params=None, server_specific_device_params=None):
    G.active_portal.portal_url = p_url
    G.active_portal.mac_address = mac
    G.active_portal.token = None

    Logger.info(f"🔍 Forsirana detekcija Stalker endpointa za {p_url}")
    detected = detect_stalker_endpoint(p_url, mac)
    if not detected:
        Logger.error(f"Auth FAILED: nijedan endpoint nije pronađen za {p_url}")
        return False

    clean_api = detected.split("?")[0]
    try:
        G.active_portal.full_api_url = clean_api
    except Exception as e:
        Logger.warning(f"♻️ active_portal immutable, rekreiram objekat ({e})")
        ap = G.active_portal
        G.active_portal = SimpleNamespace(
            portal_url=getattr(ap, "portal_url", p_url),
            mac_address=getattr(ap, "mac_address", mac),
            full_api_url=clean_api,
            user_agent=getattr(ap, "user_agent", getattr(G, "USER_AGENT_SETTING", "Mozilla/5.0")),
            stb_type=getattr(ap, "stb_type", getattr(G, "DEFAULT_STB_TYPE", "MAG250")),
            image_version=getattr(ap, "image_version", getattr(G, "DEFAULT_IMAGE_VERSION", "218")),
            hw_version=getattr(ap, "hw_version", getattr(G, "DEFAULT_HW_VERSION", "1.7-BD-00")),
            device_id=getattr(ap, "device_id", getattr(G, "DEFAULT_DEVICE_ID", "")),
            device_id2=getattr(ap, "device_id2", getattr(G, "DEFAULT_DEVICE_ID2", "")),
            signature=getattr(ap, "signature", getattr(G, "DEFAULT_SIGNATURE", "")),
            serial_number=getattr(ap, "serial_number", getattr(G, "DEFAULT_SERIAL_NUMBER", "")),
            token=None
        )

    Logger.info(f"✅ Auto-detekcija pronašla endpoint: {clean_api}")

    token = _load_token_from_cache(p_url, mac)
    if token:
        Logger.debug("Validating cached token...")
        valid_token = _get_profile_and_refresh_token(token)
        if not valid_token:
            Logger.warning("Token invalid, ponovni handshake...")
            _clear_token_cache()
            token = None
        else:
            token = valid_token

    if not token:
        handshake_token = _perform_handshake()
        if handshake_token:
            Logger.info("Handshake uspešan, validacija...")
            token = _get_profile_and_refresh_token(handshake_token)

    if token:
        G.active_portal.token = token
        _save_token_to_cache(p_url, mac, token, clean_api)
        Logger.info(f"✅ Auth SUCCEEDED za MAC {mac} ({clean_api})")
        return True
    else:
        G.active_portal.token = None
        Logger.error(f"❌ Auth FAILED za MAC {mac} ({clean_api})")
        return False


def portal_url_base(full_url):
    from urllib.parse import urlparse
    if not full_url: return "Unknown Portal"
    try:
        return urlparse(full_url).netloc
    except:
        return full_url
