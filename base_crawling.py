from concurrent.futures import ThreadPoolExecutor
import time
import pandas as pd
import requests
from requests.models import Response
from functions import logging


def robust_request(
    url: str, params: dict, max_retries: int=5, backoff_seconds: int=5
) -> Response:
    for attempt in range(max_retries):
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response
        elif response.status_code == 429:
            wait = backoff_seconds * (2 ** attempt)  # 점점 대기시간 증가
            print(f"[429] Too Many Requests. 재시도 대기: {wait}초 (시도 {attempt+1}/{max_retries})")
            time.sleep(wait)
        else:
            print(f"[{response.status_code}] 에러 발생. 중단합니다.")
            response.raise_for_status()
    raise Exception("요청 실패: Too Many Requests (최대 재시도 초과)")


def fetch_reviews_to_csv(
    appid: int, game_name: str, path: str, review_type: str, ratio_count: int, num_per_page: int=None, max_pages: int=None, language: str="english"
) -> None:
    all_reviews = []        # 모든 리뷰 저장 리스트
    cursor = "*"            # json 특정 페이지를 가리키는 주소
    cursor_seen = set()     # cursor 존재 여부 판별
    page = 0                # 페이지 매개변수가 주어졌을 때를 위한 변수, 로깅용 확인 변수

    while True:
        url = f"https://store.steampowered.com/appreviews/{appid}"
        params = {
            "json": 1,
            "language": language,
            "num_per_page": num_per_page,
            "cursor": cursor,
            "filter": "recent",  # all, recent, updated
            "review_type": review_type, # positive, negative
            "purchase_type": "all", # all, steam, non_steam_purchase
        }
        
        # 비공식 API에서 리뷰를 가져오기
        try:
            response = robust_request(url, params, max_retries=7)   # 최대 10분 대기
        except Exception as e:
            print(f"[{appid}] 요청 실패: {e}")
            break
        
        data = response.json()
        reviews = data.get("reviews", [])

        # 조기 종료) 리뷰가 없거나, 이미 방문한 cursor 위치이거나
        if not reviews or cursor in cursor_seen:
            break

        # json 데이터에서 모든 review에 대해서 정보 추출
        for r in reviews:
            # 작성자는 nested 구조라서 미리 가져옴
            author_info: dict = r.get("author", {})
            
            # 모든 정보 취합
            all_reviews.append({
                # 기본 정보
                "game_appid": appid,                    # appid: number
                "game_name": game_name,                 # 게임 이름: string
                "review_id": r.get("recommendationid"), # 리뷰(추천) 고유 ID: string
                
                # 작성자에 대한 기본 정보
                "author_steam_id": author_info.get("steamid"),                  # 작성자 Steam ID: string
                "author_num_games_owned": author_info.get("num_games_owned"),   # 작성자 보유 게임 수: number
                "author_reviews_count": author_info.get("num_reviews"),         # 작성자 리뷰 작성 수: number
                
                # 리뷰 게임에 대한 작성자 정보
                "author_playtime_forever": author_info.get("playtime_forever"),                 # 총 플레이 시간: number
                "author_playtime_last_two_week": author_info.get("playtime_last_two_weeks"),    # 최근 2주 플레이 시간: number
                "author_playtime_at_review": author_info.get("playtime_at_review"),             # 리뷰 시점 플레이 시간: number
                "author_last_played_time": author_info.get("last_played"),                      # 마지막 플레이 시각(Unix Timestamp): number
                
                # 리뷰 기본 정보
                "review_language": r.get("language"),                           # 리뷰 언어: string
                "review_text": r.get("review"),                                 # 리뷰 본문: string
                "review_created_time": r.get("timestamp_created"),              # 리뷰 작성 시간(Unix Timestamp): number
                "review_updated_time": r.get("timestamp_updated"),              # 리뷰 수정 시간(Unix Timestamp): number
                "b_game_recommendation": r.get("voted_up"),                     # 추천 여부(긍정/부정): boolean
                "review_recommendation_count": r.get("votes_up"),               # 추천 수: number
                "review_funny_count": r.get("votes_funny"),                     # 재미있어요 수: number
                "review_weighted_rating_score": r.get("weighted_vote_score"),   # 유용성 가중 점수(0~1): string
                "review_comment_count": r.get("comment_count"),                 # 댓글 수: number
                "b_author_steam_purchase": r.get("steam_purchase"),             # Steam 구매 여부: boolean
                "b_author_received_for_free": r.get("received_for_free"),       # 무료로 받았는지 여부: boolean
                "b_review_written_during_early_access": r.get("written_during_early_access"),    # 얼리 액세스 중 작성 여부: boolean
                "b_primarily_steam_deck": r.get("primarily_steam_deck"),        # 주요 게임 실행 환경이 스팀덱인지 여부:boolean
            })

        # 한 페이지를 순회하고 cursor 방문을 등록
        cursor_seen.add(cursor)
        cursor = data.get("cursor")
        page += 1
        
        # 로깅용
        print(f"{appid} log: Page {page}, {len(reviews)} reviews collected.")
        
        # 조기 종료) 페이지 매개변수가 있다면 상한 확인
        if max_pages and page >= max_pages:
            break

        # 기본 요청 밴 방지 대기
        time.sleep(1)
    
    # 원하는 개수를 채우지 못한 경우 에러 로깅깅
    if len(all_reviews) < ratio_count:
        logging(appid, game_name, review_type, len(all_reviews), ratio_count)

    # 모든 리뷰 페이지 정보를 가져온 뒤, DataFrame으로 변환 후 CSV 저장
    df = pd.DataFrame(all_reviews[:ratio_count])
    save_file_name = f"review_{appid}_{review_type}.csv"
    df.to_csv(f"{path}/{save_file_name}", index=False, encoding="utf-8-sig")
    print(f"\n✅ 총 {len(df)}개 리뷰가 review_{appid}.csv에 저장되었습니다.")


def run_parallel_review_fetch(
    appids: list[int], game_names: list[str], path: str, review_type: str, ratio_counts: int, num_per_pages: int=100, max_pages: int=5, max_workers: int=4
) -> None:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(fetch_reviews_to_csv, appid, game_name, path, review_type, ratio_count, num_per_pages, max_pages)
            for appid, game_name, ratio_count in zip(appids, game_names, ratio_counts)
        ]
        for future in futures:
            future.result()


# # Somthing run
# appids = [570] #, 3548250, 2358720, 413150]
# path = ["top_rated_200", "top_sellers_200"]
# review_type = ["positive", "negative"]
# run_parallel_review_fetch(appids, "./", review_type[0], max_workers=5, max_pages=5)