from datetime import datetime
import json
import textwrap
import os
import pandas as pd
import requests
from constants import STEAM_API_KEY as KEY, CSV_FOLDER_PATH, ROOT_PATH


def get_supported_api_list() -> json:
    base = "https://api.steampowered.com"
    interface = "ISteamWebAPIUtil"
    method = "GetSupportedAPIList"
    version = "v0001"
    format = "json"
    url = f"{base}/{interface}/{method}/{version}/?key={KEY}&format={format}"
    
    response = requests.get(url)
    api_list = response.json()
    return transform_apilist_to_df(api_list)


def transform_apilist_to_df(apilist: json) -> pd.DataFrame:
    rows = []
    for interface in apilist["apilist"]["interfaces"]:
        interface_name = interface["name"]
        for method in interface["methods"]:
            method_name = method["name"]
            version = method["version"]
            http_method = method["httpmethod"]
            parameters = method.get("parameters", [])
            for param in parameters:
                rows.append({
                    "interface": interface_name,
                    "method": method_name,
                    "version": version,
                    "http_method": http_method,
                    "param_name": param["name"],
                    "param_type": param["type"],
                    "optional": param["optional"]
                })
            if not parameters:  # 파라미터가 없을 때도 한 줄 추가
                rows.append({
                    "interface": interface_name,
                    "method": method_name,
                    "version": version,
                    "http_method": http_method,
                    "param_name": None,
                    "param_type": None,
                    "optional": None
                })
    return pd.DataFrame(rows)


def get_appid_name_dict() -> dict:
    base = "https://api.steampowered.com"
    interface = "ISteamApps"
    method = "GetAppList"
    version = "v0002"
    format = "json"
    url = f"{base}/{interface}/{method}/{version}/?key={KEY}&format={format}"
    
    response = requests.get(url)
    api_listup = response.json()
    
    appid_to_name = dict()
    name_to_appid = dict()
    for d in api_listup["applist"]["apps"]:
        appid_to_name[d["appid"]] = d["name"]
        name_to_appid[d["name"]] = d["appid"]
    
    return appid_to_name, name_to_appid


def search_appid_by_name(game_name: str) -> int:
    url = "https://store.steampowered.com/api/storesearch/"
    params = {
        "term": game_name,
        "cc": "KR",        # 국가 (한국)
        "l": "korean"      # 언어 (한국어)
    }
    res = requests.get(url, params=params)

    if res.ok:
        results = res.json().get("items", [])
        if results:
            result = results[0]
            return result["id"]


def find_appid(df: pd.DataFrame, col_nm: str) -> pd.Series:
    _, name_to_appid = get_appid_name_dict()
    return df[col_nm].apply(lambda n: name_to_appid.get(n, search_appid_by_name(n)))


def extract_appid():
    sample1 = "steam_rpg_toprated_top3000_0528.csv"
    sample2 = "steam_rpg_topsellers_top1399_0528.csv"
    df1 = pd.read_csv(os.path.join(CSV_FOLDER_PATH, sample1))
    df2 = pd.read_csv(os.path.join(CSV_FOLDER_PATH, sample2))
    df1 = df1[['appid', '게임명']]
    df2 = df2[['appid', '게임명']]
    appid_to_name, _ = get_appid_name_dict()
    df3 = pd.DataFrame([
        {"appid": appid, "게임명": name}
        for appid, name in appid_to_name.items()
    ])
    df_all = pd.concat([df1, df2, df3], ignore_index=True).drop_duplicates()
    df_all.to_csv(os.path.join(CSV_FOLDER_PATH, "appid.csv"), index=False)
    return


def logging(appid: int, game_name: str, review_type: str, crawled_review_count: int, ratio_count: int) -> None:
    cur_time = str(datetime.now().strftime('%Y%m%d%H%M%S'))
    txt = f"{cur_time}_{appid}({review_type})_({crawled_review_count} of {ratio_count}).txt"
    path = os.path.join(ROOT_PATH, "log", txt)
    
    save_text = textwrap.dedent(f"""\
        {cur_time}에 실행한 {game_name}({appid})에 대한 비공식 API 요청 개수가 부족합니다.
        받아온 개수: {crawled_review_count}, 원하는 개수: {ratio_count}, 부족한 개수: {ratio_count - crawled_review_count}
        현재 {review_type} 타입에 대해 {crawled_review_count / ratio_count * 100:.2f}% 가져왔습니다.
    """)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(save_text)
    return