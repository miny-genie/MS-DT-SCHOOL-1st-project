from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests
import time
from tqdm import tqdm
from functions import get_appid_name_map


def get_genre(appid: int) -> list[str]:
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        app_data = data.get(str(appid))
        game = app_data.get("data")
        genres = (
            [g["description"] for g in game.get("genres", [])]
            if game.get("genres")
            else None
        )
    except Exception as e:
        print(f"⚠️ {appid} 실패: {e}")
    
    return genres


def run_parallel_review_fetch(appids: list[int], max_workers: int=4) -> None:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(get_genre, appid)
            for appid in appids
        ]
        for future in futures:
            future.result()


appid_to_name, _ = get_appid_name_map()

result = []

for appid in tqdm(appid_to_name.keys()):
    result.append({"appid": appid, "genres": get_genre(appid)})

pd.DataFrame(result).to_csv("genres.csv", index=False)