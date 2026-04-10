import logging
from pathlib import Path

import uvicorn

from coc_api import AppConfig, create_app, load_coc_api_token

COC_API_BASE_URL = "https://api.clashofclans.com/v1"

# Battle log polling config for the tracked players.
TRACKED_BATTLE_LOG_TAGS = [
    "PPOLJLR2Y", # Austin
    "Q2RCJ9YLY", # fancy
    "PP2UOUPC",  # Bob
    "22QOUU2VR", # space face
    "YURLC99C8", # ruin
    "8UQC99PJY", # quynh nhu
    "LU8YGPL9J", # thanh diep
    "YCYJU8PJO", # light
    "LU9VGCPUY", # Kevin
    "YVGCLY9U9", # BSE
    "GUQ22PC2L", # wuzhen
    "QQUU9RGJR", # mheyding
    "LOJ9JJYY8", # bananasux
    "GYUUO8OVV", # yeowunnn
    "98OCPPRG",  # starkiller
    "ROJLOVQUO", # sun tzu
]
BATTLE_LOG_SYNC_INTERVAL_SECONDS = 60 * 30
BATTLE_LOG_CATEGORY_LIMIT = 50
BATTLE_LOG_DB_PATH = Path("battle_logs.sqlite3")

logging.basicConfig(level=logging.INFO)

app_config = AppConfig(
    coc_api_base_url=COC_API_BASE_URL,
    coc_api_token=load_coc_api_token(),
    tracked_battle_log_tags=TRACKED_BATTLE_LOG_TAGS,
    battle_log_sync_interval_seconds=BATTLE_LOG_SYNC_INTERVAL_SECONDS,
    battle_log_category_limit=BATTLE_LOG_CATEGORY_LIMIT,
    battle_log_db_path=BATTLE_LOG_DB_PATH,
)

app = create_app(app_config)


# def main() -> None:
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8080,
#     )


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=443,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem",
    )


if __name__ == "__main__":
    main()
