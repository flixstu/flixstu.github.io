# api.py
from __future__ import absolute_import, division, unicode_literals
import json
import requests
from urllib.parse import urlencode
import globals as G
from logger import Logger
import auth
import traceback

ENDPOINT_PATHS = [
    "stalker_portal/server/load.php",
    "stalker_portal/c/load.php",
    "server/load.php",
    "c/load.php",
    "portalstb/load.php",
    "load.php",
    "stalker_portal/c/portal.php",
    "portal.php",
    "c/portal.php",
    "stalker_portal/load.php",
    "stalker_portal/api.php",
    "api.php",
    "stalker_portal/server/api.php",
    "stalker_portal/index.php",
    "index.php",
    "stalker_portal/info.php",
    "stb_info.php",
    "stalker_portal/main/index.html",
    "stalker_portal/auth/login", # Neki noviji sistemi
]

def _detect_valid_endpoint(base_url):
    Logger.info(f"🔍 Pokrećem detekciju endpointa za {base_url} (timeout={G.REQUEST_TIMEOUT})")
    if not base_url.endswith("/"):
        base_url += "/"

    for path in ENDPOINT_PATHS:
        test_url = f"{base_url}{path}"
        try:
            r = requests.get(test_url, timeout=G.REQUEST_TIMEOUT)
            if r.status_code == 200:
                Logger.info(f"✅ Pronađen validan endpoint: {test_url}")
                return test_url
        except Exception:
            continue
    Logger.error(f"❌ Nijedan validan endpoint nije pronađen za {base_url}")
    return None


def _make_api_request(params, is_json_response=True, attempt_reauth_on_failure=True):
    if not G.active_portal or not G.active_portal.mac_address or not G.active_portal.portal_url:
        Logger.error("❌ API request failed: Portal ili MAC nisu definisani u G.active_portal.")
        return None

    detected_endpoint = _detect_valid_endpoint(G.active_portal.portal_url)
    if not detected_endpoint:
        Logger.error(f"⚠️ Endpoint detection failed for portal: {G.active_portal.portal_url}")
        return None

    try:
        G.active_portal.detected_endpoint_url = detected_endpoint
    except Exception as e:
        Logger.warning(f"♻️ active_portal immutable, rekreiram objekat ({e})")
        
        try:
            from globals import ActivePortalConfig 
        except ImportError as ie:
            Logger.critical(f"KRITIČNA GREŠKA U ADDONU (api.py): ImportError: {ie}")
            raise ie 

        G.active_portal = ActivePortalConfig(
            portal_url=G.active_portal.portal_url,
            mac_address=G.active_portal.mac_address,
            token=G.active_portal.token,
            user_agent=G.active_portal.user_agent,
            stb_type=G.active_portal.stb_type,
            image_version=G.active_portal.image_version,
            hw_version=G.active_portal.hw_version,
            serial_number=G.active_portal.serial_number,
            device_id=G.active_portal.device_id,
            device_id2=G.active_portal.device_id2,
            signature=G.active_portal.signature,
            detected_endpoint_url=detected_endpoint
        )
        Logger.info(f"✅ Auto-detekcija pronašla endpoint: {detected_endpoint}")

    final_params = params.copy()
    if 'mac' not in final_params:
        final_params['mac'] = G.active_portal.mac_address

    headers = {
        'User-Agent': G.active_portal.user_agent,
        'X-User-Agent': G.active_portal.stb_type,
        'Referer': G.active_portal.portal_url,
        'Authorization': f'Bearer {G.active_portal.token}',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    }
    cookies = {'mac': G.active_portal.mac_address}

    Logger.debug(f"API Request URL (base): {G.active_portal.full_api_url}")
    Logger.debug(f"API Request params: {final_params}")

    try:
        response = requests.get(
            G.active_portal.full_api_url,
            params=final_params,
            headers=headers,
            cookies=cookies,
            timeout=G.REQUEST_TIMEOUT
        )

        Logger.debug(f"Actual API URL called: {response.url}")

        if response.status_code == 401 or "Authorization failed" in response.text:
            Logger.warning(f"⚠️ Authorization failed ({response.status_code}). Re-authenticating...")
            if attempt_reauth_on_failure:
                if auth.authenticate_mac(G.active_portal.portal_url, G.active_portal.mac_address):
                    Logger.info("🔁 Re-authentication successful, retrying API request.")
                    return _make_api_request(params, is_json_response, attempt_reauth_on_failure=False)
                else:
                    Logger.error("❌ Re-authentication failed.")
                    return None
            else:
                Logger.error("🚫 Already attempted reauth. Stopping.")
                return None

        response.raise_for_status()

        if is_json_response:
            try:
                data = response.json()
                if 'js' in data and data['js'] is not None:
                    return data['js']
                else:
                    return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                Logger.error("❌ API response not valid JSON.")
                return None
        else:
            return response.text

    except requests.exceptions.RequestException as e:
        Logger.error(f"🌐 API request error ({params.get('action', '')}): {e}")
        return None
    except Exception as e:
        import traceback
        Logger.error(f"💥 Unexpected API error: {e}\n{traceback.format_exc()}")
        return None


# === PUBLIC API FUNKCIJE === #

def get_genres(content_type='vod'):
    return _make_api_request({'type': content_type, 'action': 'get_genres'})

def get_all_channels():
    return _make_api_request({'type': 'itv', 'action': 'get_all_channels'})

def get_ordered_list(content_type, addition_params=None):
    params = {'type': content_type, 'action': 'get_ordered_list'}
    if addition_params:
        params.update(addition_params)
    return _make_api_request(params)

def create_stream_link(content_type_for_api, cmd_or_media_id, series_episode_id=None):
    params = {'type': content_type_for_api, 'action': 'create_link', 'cmd': cmd_or_media_id}
    if content_type_for_api != 'itv' and series_episode_id is not None:
        params['series'] = str(series_episode_id)
    response_data_js = _make_api_request(params)
    if response_data_js and isinstance(response_data_js, dict) and 'cmd' in response_data_js:
        stream_cmd = response_data_js['cmd']
        if stream_cmd.lower().startswith("ffmpeg "):
            return stream_cmd[7:]
        elif stream_cmd.lower().startswith("auto "):
            return stream_cmd[5:]
        return stream_cmd
    return None

def get_profile_info():
    return _make_api_request({'type': 'stb', 'action': 'get_profile'})

def set_favourite(content_type, media_id, is_tv_channel=False):
    params = {'type': 'itv' if is_tv_channel else content_type, 'action': 'set_fav'}
    params['fav_add' if is_tv_channel else 'video_id'] = media_id
    return _make_api_request(params)

def remove_favourite(content_type, media_id, is_tv_channel=False):
    params = {'type': 'itv' if is_tv_channel else content_type, 'action': 'set_fav'}
    params['fav_del' if is_tv_channel else 'video_id'] = media_id
    return _make_api_request(params)