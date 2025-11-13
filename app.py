from flask import Flask, jsonify
import aiohttp
import asyncio
import json
import os
from byte import encrypt_api, Encrypt_ID
from visit_count_pb2 import Info  # Import the generated protobuf class

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return '', 204

async def load_tokens(server_name):
    try:
        base_url = os.getenv("TOKEN_BASE_URL")
        if not base_url:
            raise ValueError("TOKEN_BASE_URL environment variable is not set.")
        if server_name == "PK":
            path = "PK/token_PK.json"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            path = "BR/token_BR.json"
        else:
            path = "BD/token_BD.json"

        url = base_url + path
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    # Force decode as JSON, even if mimetype is text/plain
                    data = json.loads(await resp.text())
                    tokens = [item["token"] for item in data if "token" in item and item["token"] not in ["", "N/A"]]
                    return tokens
                else:
                    app.logger.error(f"❌ Failed to fetch tokens from {url}: Status {resp.status}")
                    return []
    except Exception as e:
        app.logger.error(f"❌ Token load error for {server_name}: {e}")
        return []

def get_url(server_name):
    if server_name == "PK":
        return "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
    else:
        return "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"

def parse_protobuf_response(response_data):
    try:
        info = Info()
        info.ParseFromString(response_data)
        
        player_data = {
            "uid": info.AccountInfo.UID if info.AccountInfo.UID else 0,
            "nickname": info.AccountInfo.PlayerNickname if info.AccountInfo.PlayerNickname else "",
            "likes": info.AccountInfo.Likes if info.AccountInfo.Likes else 0,
            "region": info.AccountInfo.PlayerRegion if info.AccountInfo.PlayerRegion else "",
            "level": info.AccountInfo.Levels if info.AccountInfo.Levels else 0
        }
        return player_data
    except Exception as e:
        app.logger.error(f"❌ Protobuf parsing error: {e}")
        return None

async def visit(session, url, token, uid, data):
    headers = {
        "ReleaseVersion": "OB51",
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
        app.logger.error(f"❌ Visit error: {e}")
        return False, None

async def send_visits_in_batches(tokens, uid, server_name):
    url = get_url(server_name)
    connector = aiohttp.TCPConnector(limit=0)
    total_success = 0
    total_sent = 0
    first_success_response = None
    player_info = None
    batch_size = 100
    
    async with aiohttp.ClientSession(connector=connector) as session:
        encrypted = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
        data = bytes.fromhex(encrypted)

        for i in range(0, len(tokens), batch_size):
            current_batch_tokens = tokens[i:i + batch_size]
            tasks = [
                asyncio.create_task(visit(session, url, token, uid, data))
                for token in current_batch_tokens
            ]
            results = await asyncio.gather(*tasks)
            
            if first_success_response is None:
                for success, response in results:
                    if success and response is not None:
                        first_success_response = response
                        player_info = parse_protobuf_response(response)
                        break
            
            batch_success = sum(1 for r, _ in results if r)
            total_success += batch_success
            total_sent += len(current_batch_tokens)

            print(f"Batch sent: {len(current_batch_tokens)}, Success in batch: {batch_success}, Total success so far: {total_success}")
            
            if batch_success > 0:
                print("Successfully sent a batch, sending next batch...")
            else:
                print("No success in this batch, continuing to next batch...")

    return total_success, total_sent, player_info

@app.route('/<string:server>/<int:uid>', methods=['GET'])
def send_visits(server, uid):
    server = server.upper()
    tokens = asyncio.run(load_tokens(server))
    target_success = len(tokens) # Set target_success to the number of available tokens

    if not tokens:
        return jsonify({"error": "❌ No valid tokens found"}), 500

    print(f"🚀 Sending visits to UID: {uid} using {len(tokens)} tokens")
    print(f"Waiting for total {target_success} successful visits...")

    total_success, total_sent, player_info = asyncio.run(send_visits_in_batches(
        tokens, uid, server
    ))

    if player_info:
        player_info_response = {
            "fail": target_success - total_success,
            "level": player_info.get("level", 0),
            "likes": player_info.get("likes", 0),
            "nickname": player_info.get("nickname", ""),
            "region": player_info.get("region", ""),
            "success": total_success,
            "uid": player_info.get("uid", 0)
        }
        return jsonify(player_info_response), 200
    else:
        return jsonify({"error": "Could not decode player information"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)