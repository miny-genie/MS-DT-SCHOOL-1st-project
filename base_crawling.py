from concurrent.futures import ThreadPoolExecutor
import time
import pandas as pd
import requests
from functions import logging, transform_datetime


def robust_request(url: str, params: dict, max_retries: int=5, backoff_seconds: int=5) -> requests.Response:
    for attempt in range(max_retries):
        response = requests.get(url, params=params)
        if response.ok:
            return response
        elif response.status_code == 429:
            wait = backoff_seconds * (2 ** attempt)  # 대기시간 점차 증가
            print(f"[⚠️WARNING] Code 429 Too Many Requests. 재시도 대기: {wait}초 (시도 {attempt + 1}/{max_retries})")
            time.sleep(wait)
        else:
            print(f"[❌ERROR] Code {response.status_code} Request failed.")
            response.raise_for_status()
    raise RuntimeError("[ERROR] Too Many Requests (최대 재시도 초과)")


def parse_review_data(appid: int, game_name: str, review: dict) -> dict:
    author = review.get("author", {})
    return {
        # 기본 정보
        "game_appid": str(appid),               # appid: string
        "game_name": game_name,                 # 게임 이름: string
        "review_id": review.get("recommendationid"), # 리뷰(추천) 고유 ID: string

        # 작성자에 대한 기본 정보
        "author_steam_id": author.get("steamid"),                  # 작성자 Steam ID: string
        "author_num_games_owned": author.get("num_games_owned"),   # 작성자 보유 게임 수: number
        "author_reviews_count": author.get("num_reviews"),         # 작성자 리뷰 작성 수: number

        # 리뷰 게임에 대한 작성자 정보
        "author_playtime_forever": author.get("playtime_forever"),                 # 총 플레이 시간: number
        "author_playtime_last_two_week": author.get("playtime_last_two_weeks"),    # 최근 2주 플레이 시간: number
        "author_playtime_at_review": author.get("playtime_at_review"),             # 리뷰 시점 플레이 시간: number
        "author_last_played_time": transform_datetime(author.get("last_played")),  # 마지막 플레이 시각(Unix Timestamp): string

        # 리뷰 기본 정보
        "review_language": review.get("language"),                                   # 리뷰 언어: string
        "review_text": review.get("review"),                                         # 리뷰 본문: string
        "review_created_time": transform_datetime(review.get("timestamp_created")),  # 리뷰 작성 시간(Unix Timestamp): string
        "review_updated_time": transform_datetime(review.get("timestamp_updated")),  # 리뷰 수정 시간(Unix Timestamp): string
        "b_game_recommendation": review.get("voted_up"),                             # 추천 여부(긍정/부정): boolean
        "review_recommendation_count": review.get("votes_up"),                       # 추천 수: number
        "review_funny_count": review.get("votes_funny"),                             # 재미있어요 수: number
        "review_weighted_rating_score": review.get("weighted_vote_score"),           # 유용성 가중 점수(0~1): float
        "review_comment_count": review.get("comment_count"),                         # 댓글 수: number
        "b_author_steam_purchase": review.get("steam_purchase"),                     # Steam 구매 여부: boolean
        "b_author_received_for_free": review.get("received_for_free"),               # 무료로 받았는지 여부: boolean
        "b_review_written_during_early_access": review.get("written_during_early_access"),    # 얼리 액세스 중 작성 여부: boolean
        "b_primarily_steam_deck": review.get("primarily_steam_deck"),                # 주요 게임 실행 환경이 스팀덱인지 여부:boolean
    }


def fetch_reviews_to_csv(appid: int, game_name: str, path: str, review_type: str, ratio_count: int, num_per_page: int=None, max_pages: int=None, language: str="english") -> None:
    all_reviews, cursor_seen = [], set()        
    cursor, page = "*", 0
    
    while True:
        url = f"https://store.steampowered.com/appreviews/{appid}"
        params = {
            "json": 1,
            "language": language,
            "purchase_type": "all",     # all, steam, non_steam_purchase
            "filter": "recent",         # all, recent, updated
            "num_per_page": num_per_page,
            "review_type": review_type, # positive, negative
            "cursor": cursor,
        }
        # 로그를 위한 실제 url 조합
        real_url = f"https://store.steampowered.com/appreviews/{appid}?{'&'.join([k + '=' + str(v) for k, v in params.items()])}"
        
        # 비공식 API에서 리뷰를 가져오기(최대 10분 대기)
        try:
            response = robust_request(url, params, max_retries=7)
        except Exception as e:
            print(f"[❌ERROR]: {appid} 요청 실패 {e}")
            break
        
        data = response.json()
        reviews = data.get("reviews", [])
        if not reviews or cursor in cursor_seen:
            logging(appid, game_name, review_type, 0, ratio_count, real_url)
            print(f"[❌ERROR]: {appid}({page}/{max_pages})_{review_type} 가져온 데이터 없음")
            print(real_url)
            break
            
        all_reviews.extend([parse_review_data(appid, game_name, review) for review in reviews])
        cursor_seen.add(cursor)
        cursor = data.get("cursor")
        page += 1
        
        # 로깅용
        print(f"[✅INFO]: {appid}({page}/{max_pages}), {len(reviews)} reviews collected.")
        if max_pages and page >= max_pages:
            break

        # 기본 요청 밴 방지 대기
        time.sleep(1)
    
    # 원하는 개수를 채우지 못한 경우 에러 로깅
    if len(all_reviews) < ratio_count:
        logging(appid, game_name, review_type, len(all_reviews), ratio_count, real_url)

    df = pd.DataFrame(all_reviews[:ratio_count])
    df.to_csv(f"{path}/review_{appid}_{review_type}.csv", index=False, encoding="utf-8-sig")
    print(f"[✅INFO] 총 {len(df)}개 리뷰가 review_{appid}.csv에 저장")


def run_parallel_review_fetch(appids: list[int], game_names: list[str], path: str, review_type: str, ratio_counts: int, num_per_pages: int, max_pages: list[int], max_workers: int=4) -> None:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(fetch_reviews_to_csv, appid, game_name, path, review_type, ratio_count, num_per_pages, max_page)
            for appid, game_name, ratio_count, max_page in zip(appids, game_names, ratio_counts, max_pages)
        ]
        for f in futures:
            f.result()