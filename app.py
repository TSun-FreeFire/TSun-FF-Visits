import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, render_template

import aiohttp
from byte import encrypt_api, Encrypt_ID
from google.protobuf import json_format

# Import generated protobuf classes
try:
    from proto import AccountPersonalShow_pb2
except ImportError:
    logging.error("Could not import proto files. Ensure the 'proto' directory exists.")
    sys.exit(1)

AccountPersonalShowInfo = getattr(AccountPersonalShow_pb2, "AccountPersonalShowInfo")

# --- Remote configuration (fetched from gist on every call, never cached) ---
CONFIG_URL = "https://gist.githubusercontent.com/SaeedX302/b8277fdd6a2e71b599a39299f3ab3545/raw/config.json"

async def fetch_config():
    """Fetch config.json fresh from the remote gist on every call (no caching)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(CONFIG_URL) as resp:
            resp.raise_for_status()
            # Force JSON decode even if served as text/plain
            return json.loads(await resp.text())

def fetch_config_sync():
    """Synchronous wrapper for use inside Flask route handlers."""
    return asyncio.run(fetch_config())

app = Flask(__name__, static_folder="assets", static_url_path="/assets")
APP_START_TIME = time.monotonic()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    uptime_seconds = round(time.monotonic() - APP_START_TIME, 3)
    return jsonify({"status": "ok", "uptime_seconds": uptime_seconds}), 200

@app.route('/config', methods=['GET'])
def config_info():
    """Expose public-facing config values fetched live from the gist."""
    config = fetch_config_sync()
    return jsonify({
        "version": config.get("version"),
        "release_version": config.get("RELEASEVERSION"),
        "next_update": config.get("next_update"),
        "owner": config.get("owner"),
    }), 200

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REGION_OFFSETS = {
    "BD": 6.0, "IND": 5.5, "ME": 3.0, "NA": -5.0, "PK": 5.0,
    "BR": -3.0, "US": -5.0, "SAC": -3.0, "VN": 7.0, "RU": 3.0,
    "SG": 8.0, "ID": 7.0, "TW": 8.0, "TH": 7.0, "EU": 1.0,
}

# --- Helper Functions (Previously in tsunxkitten.py) ---

async def load_tokens(server_name):
    try:
        base_url = "https://raw.githubusercontent.com/TSun-FreeFire/TSun-FreeFire-Storage/main/Spam-api/"
        
        server_map = {
            "BD": "token_bd.json",
            "IND": "token_ind.json",
            "ME": "token_me.json",
            "NA": "token_na.json",
            "PK": "token_pk.json",
            "BR": "token_br.json",
            "US": "token_na.json",
            "SAC": "token_br.json",
        }

        file_name = server_map.get(server_name, "token_bd.json")
        url = base_url + file_name
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    # Force decode as JSON, even if mimetype is text/plain
                    data = json.loads(await resp.text())
                    tokens = [item["token"] for item in data if "token" in item and item["token"] not in ["", "N/A"]]
                    return tokens
                else:
                    logger.error(f"❌ Failed to fetch tokens from {url}: Status {resp.status}")
                    return []
    except Exception as e:
        logger.error(f"❌ Token load error for {server_name}: {e}")
        return []

def get_url(server_name, config):
    # Base client URLs come from the remote config -> client_url
    client_url = config.get("client_url", {})
    if server_name == "IND":
        base = client_url.get("ind", "https://client.ind.freefiremobile.com/")
    elif server_name in {"BR", "US", "SAC", "NA"}:
        base = client_url.get("us", "https://client.us.freefiremobile.com/")
    else:
        # PK and all other regions use the global endpoint
        base = client_url.get("global", "https://clientbp.ggpolarbear.com/")
    return base.rstrip("/") + "/GetPlayerPersonalShow"

def parse_basic_protobuf_response(response_data):
    # This is the lighter parsing used during mass visits
    try:
        info = AccountPersonalShowInfo()
        info.ParseFromString(response_data)
        basic_info = info.basic_info
        
        player_data = {
            "uid": basic_info.account_id if basic_info.account_id else 0,
            "nickname": basic_info.nickname if basic_info.nickname else "",
            "likes": basic_info.liked if basic_info.liked else 0,
            "region": basic_info.region if basic_info.region else "",
            "level": basic_info.level if basic_info.level else 0
        }
        return player_data
    except Exception as e:
        logger.error(f"❌ Protobuf parsing error: {e}")
        return None

async def visit(session, url, token, uid, data, release_version):
    headers = {
        "ReleaseVersion": release_version,
        "X-GA": "v1 1",
        "Authorization": f"Bearer {token}",
        "Host": url.replace("https://", "").split("/")[0]
    }
    try:
        async with session.post(url, headers=headers, data=data, ssl=False) as resp:
            if resp.status == 200:
                response_data = await resp.read()
                return True, response_data
            else:
                return False, None
    except Exception as e:
        logger.error(f"❌ Visit error: {e}")
        return False, None

async def send_visits_in_batches(tokens, uid, server_name, config):
    url = get_url(server_name, config)
    release_version = config.get("RELEASEVERSION", "OB54")
    connector = aiohttp.TCPConnector(limit=0)
    total_success = 0
    total_sent = 0
    first_success_response = None
    player_info = None
    batch_size = 100
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Generate encrypted payload for the visit
        try:
           encrypted_id = Encrypt_ID(str(uid))
           if encrypted_id is None:
               raise ValueError("Unable to encrypt UID")
           encrypted = encrypt_api(f"08{encrypted_id}1801")
           data = bytes.fromhex(encrypted)
        except Exception:
           return 0, 0, None # Fail gracefully if encryption fails

        for i in range(0, len(tokens), batch_size):
            current_batch_tokens = tokens[i:i + batch_size]
            tasks = [
                asyncio.create_task(visit(session, url, token, uid, data, release_version))
                for token in current_batch_tokens
            ]
            results = await asyncio.gather(*tasks)
            
            if first_success_response is None:
                for success, response in results:
                    if success and response is not None:
                        first_success_response = response
                        # Parse basic info from the first successful hit
                        player_info = parse_basic_protobuf_response(response)
                        break
            
            batch_success = sum(1 for r, _ in results if r)
            total_success += batch_success
            total_sent += len(current_batch_tokens)
            
            # Simple logging or removed to be quieter
            # print(f"Batch sent... Success: {batch_success}")

    return total_success, total_sent, player_info

# ... (Existing formatting logic remains) ...

def format_timestamp_with_timezone(timestamp, region):
    if timestamp is None:
        return None
    
    try:
        # Convert string/int to strict integer
        ts = int(str(timestamp))
        
        # Filter invalid ranges
        if ts < 100000000: # Too small
            return str(ts)
            
        if ts > 10000000000: # Likely milliseconds, convert to seconds
            ts /= 1000.0
        
        # Get Timezone
        offset = REGION_OFFSETS.get(region, 0)
        tz = timezone(timedelta(hours=offset))
        
        # Format
        dt = datetime.fromtimestamp(ts, tz)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        logger.error(f"Timestamp formatting error for {timestamp}: {e}")
        return str(timestamp)

def format_timestamps_in_dict(data_dict, region):
    if not isinstance(data_dict, dict):
        return data_dict
        
    new_dict = {}
    for k, v in data_dict.items():
        key_lower = str(k).lower()
        if ("time" in key_lower or "at" in key_lower or "date" in key_lower) and isinstance(v, (int, float)):
             new_dict[k] = format_timestamp_with_timezone(v, region)
        elif isinstance(v, dict):
             new_dict[k] = format_timestamps_in_dict(v, region)
        elif isinstance(v, list):
             new_dict[k] = [format_timestamps_in_dict(item, region) if isinstance(item, dict) else item for item in v]
        else:
             new_dict[k] = v
    return new_dict

async def fetch_player_data(uid, server, tokens=None, config=None):
    if config is None:
        config = await fetch_config()
    url = get_url(server, config)
    release_version = config.get("RELEASEVERSION", "OB54")
    if not tokens:
        tokens = await load_tokens(server)
    if not tokens:
        logger.error(f"No tokens found for server {server}")
        return None
    
    # Payload matches app.py logic
    # We continue to use the byte.py encryption for request generation as it works
    try:
        encrypted_id = Encrypt_ID(str(uid))
        if encrypted_id is None:
            raise ValueError("Unable to encrypt UID")
        encrypted = encrypt_api(f"08{encrypted_id}1801")
    except Exception as e:
        logger.error(f"Failed to encrypt UID {uid}: {e}")
        return None
        
    data_bytes = bytes.fromhex(encrypted)
    
    # Try first 3 tokens
    max_attempts = 3
    tokens_to_try = tokens[:max_attempts]
    
    for i, token in enumerate(tokens_to_try):
        headers = {
            "ReleaseVersion": release_version,
            "X-GA": "v1 1",
            "Authorization": f"Bearer {token}",
            "Host": url.replace("https://", "").split("/")[0],
            "Content-Type": "application/octet-stream",
            "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.7499.146 Mobile Safari/537.36"
        }

        async with aiohttp.ClientSession() as session:
            try:
                if i > 0:
                    await asyncio.sleep(0.5)
                    
                async with session.post(url, headers=headers, data=data_bytes, ssl=False) as resp:
                    if resp.status == 200:
                        response_data = await resp.read()
                        print(f"Success with token index {i}")
                        return response_data
                    elif resp.status == 429:
                        logger.warning(f"Token {i} rate limited (429). Trying next token...")
                    else:
                        logger.warning(f"Token {i} failed with status {resp.status}. Trying next token...")
            except Exception as e:
                logger.error(f"Error fetching data with token {i}: {e}")
                
    logger.error("All attempts failed. The UID might be incorrect.")
    return None

def process_data_with_schema(binary_data, region):
    try:
        # Step A: Convert bytes to Protobuf Object using the schema
        proto_obj = AccountPersonalShowInfo()
        proto_obj.ParseFromString(binary_data)

        # Step B: Convert Protobuf Object to JSON string
        json_str = json_format.MessageToJson(proto_obj)

        # Step C: Load into Python Dictionary
        data = json.loads(json_str)

        # Extract fields using the schema structure
        basic_info = data.get("basicInfo", {})
        profile_info = data.get("profileInfo", {})
        clan_info = data.get("clanBasicInfo", {})
        captain_info = data.get("captainBasicInfo", {})
        pet_info = data.get("petInfo", {})
        social_info = data.get("socialInfo", {})
        credit_score_info = data.get("creditScoreInfo", {})

        # Helper to safely stringify IDs
        def str_safe(val):
            return str(val) if val is not None else None

        # Get actual region from response data, fallback to parameter if not available
        actual_region = basic_info.get("region") if basic_info.get("region") else region

        result = {
            "AccountInfo": {
                "AccountName": basic_info.get("nickname"),
                "AccountLevel": basic_info.get("level"),
                "AccountEXP": basic_info.get("exp"),
                "AccountRegion": actual_region,
                "AccountLikes": basic_info.get("liked"),
                "AccountLastLogin": format_timestamp_with_timezone(
                    basic_info.get("lastLoginAt"), actual_region
                ),
                "AccountCreateTime": format_timestamp_with_timezone(
                    basic_info.get("createAt"), actual_region
                ),
                "AccountSeasonId": basic_info.get("seasonId"),
            },
            "AccountProfileInfo": {
                "BrMaxRank": basic_info.get("maxRank"),
                "BrRankPoint": basic_info.get("rankingPoints"),
                "CsMaxRank": basic_info.get("csMaxRank"),
                "CsRankPoint": basic_info.get("csRankingPoints"),
                "ShowBrRank": basic_info.get("showBrRank"),
                "ShowCsRank": basic_info.get("showCsRank"),
                "Title": basic_info.get("title")
            },
            "EquippedItemsInfo": {
                "EquippedAvatarId": basic_info.get("headPic"),
                "EquippedBPBadges": basic_info.get("badgeCnt"),
                "EquippedBPID": basic_info.get("badgeId"),
                "EquippedBannerId": basic_info.get("bannerId"),
                "EquippedOutfit": profile_info.get("clothes", []),
                "EquippedWeapon": basic_info.get("weaponSkinShows", []),
                "EquippedSkills": profile_info.get("equipedSkills", [])
            },
            "SocialInfo": format_timestamps_in_dict(social_info, actual_region),
            "PetInfo": format_timestamps_in_dict(pet_info, actual_region),
            "AccountType": basic_info.get("accountType"),
            "ReleaseVersion": basic_info.get("releaseVersion"),
            "CreditScoreInfo": credit_score_info,
            "GuildInfo": {
                "GuildCapacity": clan_info.get("capacity"),
                "GuildID": str_safe(clan_info.get("clanId")),
                "GuildLevel": clan_info.get("clanLevel"),
                "GuildMember": clan_info.get("memberNum"),
                "GuildName": clan_info.get("clanName"),
                "GuildOwner": str_safe(clan_info.get("captainId"))
            },
            "GuildOwnerInfo": format_timestamps_in_dict(captain_info, actual_region)
        }
        return result

    except Exception as e:
        logger.error(f"Failed to decode Protobuf with schema: {str(e)}")
        return None

@app.route('/info/<string:uid>', methods=['GET'])
def get_player_info_auto(uid):
    """Auto-detect region by trying all available servers"""
    print(f"Fetching info for UID: {uid} (auto-detecting region)...")
    
    # List of unique servers to try (avoiding duplicates like US->NA, SAC->BR)
    servers_to_try = ["BD", "IND", "ME", "NA", "PK", "BR", "US", "SAC"]
    
    for server in servers_to_try:
        print(f"Trying server: {server}...")
        binary_data = asyncio.run(fetch_player_data(uid, server))
        
        if binary_data:
            print(f"Fetch successful on server: {server}. Processing with Schema...")
            result = process_data_with_schema(binary_data, server)
            if result:
                return jsonify(result), 200
    
    # If all servers failed
    return jsonify({"error": "Invalid UID. Could not find player on any server."}), 404

@app.route('/info/<string:server>/<string:uid>', methods=['GET'])
def get_player_info(server, uid):
    server = server.upper()
    print(f"Fetching info for UID: {uid} on Server: {server}...")
    
    # Run the async fetch logic safely within the sync route using asyncio.run
    binary_data = asyncio.run(fetch_player_data(uid, server))
    
    if binary_data:
        print("Fetch successful. Processing with Schema...")
        result = process_data_with_schema(binary_data, server)
        if result:
            return jsonify(result), 200
        else:
            return jsonify({"error": "Failed to decode data"}), 500
    else:
        return jsonify({"error": "Invalid UID or Server (Check UID and Server)"}), 404

async def background_visit_task(tokens, uid, server, config):
    """Runs the visit batch 5 times in the background."""
    for i in range(5):
        logger.info(f"Starting background visit run {i+1}/5 for UID {uid}")
        await send_visits_in_batches(tokens, uid, server, config)
        # Optional: Add small delay between runs if needed
        # await asyncio.sleep(1)

@app.route('/visit/<string:server>/<int:uid>', methods=['GET'])
def send_visits_endpoint(server, uid):
    server = server.upper()
    
    # Run the initial token load
    tokens = asyncio.run(load_tokens(server))
    
    if not tokens:
        return jsonify({"error": "❌ No valid tokens found"}), 500

    token_count = len(tokens)
    projected_success = token_count * 5

    # Fetch the remote config once for this request (used by pre-fetch + background visits)
    config = fetch_config_sync()

    # Fetch player info BEFORE starting visits to provide better UX
    # Default values in case fetch fails
    real_nickname = "Processing..."
    real_level = 0
    real_likes = 0

    try:
        # Use the tokens we already loaded
        binary_data = asyncio.run(fetch_player_data(uid, server, tokens=tokens, config=config))
        if binary_data:
            player_info = parse_basic_protobuf_response(binary_data)
            if player_info:
                real_nickname = player_info.get("nickname", "Processing...")
                real_level = player_info.get("level", 0)
                real_likes = player_info.get("likes", 0)
    except Exception as e:
        logger.error(f"Failed to pre-fetch player info for {uid}: {e}")

    print(f"🚀 Triggering 5x visits for UID: {uid}. Tokens: {token_count}. Projected Outcome: {projected_success}")

    # Helper function to run the background task in a new event loop
    # because Flask's dev server is synchronous
    def run_async_background():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(background_visit_task(tokens, uid, server, config))
        loop.close()

    # Start the background thread
    import threading
    thread = threading.Thread(target=run_async_background)
    thread.daemon = True # Ensure thread dies if main app dies
    thread.start()

    # Return IMMEDIATE response with 5x projection AND real info
    response = {
        "fail": 0, # Assuming all go well for the projection
        "level": real_level,
        "likes": real_likes, 
        "nickname": real_nickname,
        "region": server,
        "success": projected_success,
        "uid": uid,
        "message": "Request received. Sending 5x visits in background."
    }
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
