from datetime import datetime
import json
import re
import textwrap
import os
import glob
import numpy as np
import pandas as pd
import requests
from constants import STEAM_API_KEY as KEY, CSV_FOLDER_PATH, DTYPE_MAP, ROOT_PATH, ENCODING_TYPE


def round_up_to_100(x: int) -> int:
    return int(np.ceil(x / 100))


def transform_datetime(unix_timestamp: int) -> str:
    if unix_timestamp is None:
        return ""
    return datetime.fromtimestamp(unix_timestamp).strftime("%Y%m%d%H%M%S")


def logging(appid: int, game_name: str, review_type: str, crawled_review_count: int, ratio_count: int, url: str) -> None:
    cur_time = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{cur_time}_{appid}({review_type})_({crawled_review_count} of {ratio_count}).txt"
    path = os.path.join(ROOT_PATH, "log", filename)
    
    text = textwrap.dedent(f"""\
        {cur_time} 실행: {game_name}({appid})에 대한 비공식 API 요청 개수가 부족
        수집: {crawled_review_count} / 목표: {ratio_count} (부족: {ratio_count - crawled_review_count})
        비율: {review_type} 타입에 대해 {crawled_review_count / ratio_count * 100:.2f}% 수집
        {url}
    """)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def merge_pos_neg(folder_path: str) -> None:
    """
    지정한 폴더 내의 review_{appid}_positive.csv와 review_{appid}_negative.csv 파일이
    모두 존재하고 비어 있지 않을 때만 병합. 실패한 경우만 로그 출력하며,
    어떤 폴더(top_rated_200 / top_sellers_200)에서 실패했는지 명시.

    Parameters:
        folder_path (str): 리뷰 파일들이 저장된 폴더 경로
    """
    folder_name = os.path.basename(folder_path.rstrip("/\\"))  # 폴더명 추출
    files = os.listdir(folder_path)
    appids = {
        _match.group(1)
        for filename in files
        if (_match := re.match(r"review_(\d+)_(positive|negative)\.csv", filename))
    }
    
    for appid in appids:
        pos_file = os.path.join(folder_path, f"review_{appid}_positive.csv")
        neg_file = os.path.join(folder_path, f"review_{appid}_negative.csv")
        merged_file = os.path.join(folder_path, f"review_{appid}.csv")
        
        has_pos = os.path.exists(pos_file) and os.path.getsize(pos_file) > 0
        has_neg = os.path.exists(neg_file) and os.path.getsize(neg_file) > 0
                
        if has_pos and has_neg:
            try:
                df_pos = pd.read_csv(pos_file, dtype=DTYPE_MAP, encoding=ENCODING_TYPE)
                df_neg = pd.read_csv(neg_file, dtype=DTYPE_MAP, encoding=ENCODING_TYPE)
                pd.concat(
                    [df_pos, df_neg],
                    ignore_index=True
                ).to_csv(merged_file, index=False, encoding=ENCODING_TYPE)
                os.remove(pos_file)
                os.remove(neg_file)
            except Exception as e:
                print(f"[❌ERROR] 병합 실패 ({folder_name}): review_{appid}_ → CSV 파싱 오류: {e}")
        else:
            missing = []
            if not has_pos:
                missing.append("positive (누락 또는 비어 있음)")
            if not has_neg:
                missing.append("negative (누락 또는 비어 있음)")
            print(f"[❌ERROR] 병합 실패 ({folder_name}): review_{appid}_ → {', '.join(missing)}")


def concat_merged_reviews(folder_path: str, output_file: str) -> None:
    pattern = os.path.join(folder_path, "review_*.csv")
    target_files = [
        f for f in glob.glob(pattern)
        if not re.match(
            r".*review_\d+_(positive|negative)\.csv$",
            os.path.basename(f)
        )
    ]
    
    if not target_files:
        print(f"[⚠️WARNING] 병합 대상 파일이 없음: {folder_path}")
    
    merged_df = pd.concat([
        pd.read_csv(f, dtype=DTYPE_MAP, encoding=ENCODING_TYPE)
        for f in target_files
    ], ignore_index=True)
    
    output_path = os.path.join(folder_path, output_file)
    merged_df.to_csv(output_path, index=False, encoding=ENCODING_TYPE)
    print(f"[✅INFO] 종합 병합 완료: {output_path}")
    
    for f in target_files:
        os.remove(f)

# ===============================================================================


def find_total_review(appid: int):
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "language": "english",
        "cursor": "*",
        "filter": "recent",  # all, recent, updated
        "purchase_type": "all",
    }
    res = requests.get(url, params=params)
    data: dict = res.json()
    total_reviews = data.get("query_summary", {}).get("total_reviews", 0)
    return total_reviews


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


