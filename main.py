import os
import pandas as pd
from base_crawling import run_parallel_review_fetch as run
from constants import CSV_FOLDER_PATH, ENCODING_TYPE
from functions import merge_pos_neg, concat_merged_reviews, round_up_to_100


def get_appids_and_gamenames(file_name: str, target_review_count: int) -> tuple[list[int], list[int]]:
    if "all" in file_name:
        df_all = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name), encoding=ENCODING_TYPE)
        return df_all['appid'].tolist(), df_all['name'].tolist()
    else:
        df_rev = pd.read_csv(os.path.join(CSV_FOLDER_PATH, "appid_game-name_eng-rev-cnt.csv"), encoding=ENCODING_TYPE)
        df_rev = df_rev.drop_duplicates(subset=['app_id'])[['app_id', 'english_review_count']]
        
        df_top = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name), encoding=ENCODING_TYPE)[['app_id', '게임이름']]
        df = df_top.merge(df_rev, how='left', on='app_id')
        df = df[df['english_review_count'] >= target_review_count]
        return df['app_id'].tolist(), df['게임이름'].tolist()


def calculate_ratio(appids: list[int], file_name: str, target_review_count: int) -> tuple[list[int], list[int]]:
    if "all" in file_name:
        df_all = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name), encoding=ENCODING_TYPE)
        df_all['pos_count'] = df_all['eng_review_positive'] * target_review_count // 100
        df_all['neg_count'] = target_review_count - df_all['pos_count']
        return df_all['pos_count'].tolist(), df_all['neg_count'].tolist()
    else:
        df = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name), encoding=ENCODING_TYPE)
        df = df[df['app_id'].isin(appids)]
        df['pos_count'] = df['긍정적인 평가 비율'] * target_review_count // 100
        df['neg_count'] = target_review_count - df['pos_count']
        return df['pos_count'].tolist(), df['neg_count'].tolist()


def process_reviews(file_name: str, folder_name: str, target_game_count: int, target_review_count: int, max_workers: int) -> None:
    appids, gamenames = get_appids_and_gamenames(file_name, target_review_count)
    pos_counts, neg_counts = calculate_ratio(appids, file_name, target_review_count)
    
    appids, gamenames = appids[:target_game_count], gamenames[:target_game_count]
    pos_counts, neg_counts = pos_counts[:target_game_count], neg_counts[:target_game_count]
    pos_pages, neg_pages = map(round_up_to_100, pos_counts), map(round_up_to_100, neg_counts)
    folder_path = os.path.join("file", folder_name)
    
    print(f"[RUN] {folder_name} 리뷰 수집 시작({len(appids)}개 게임)")
    run(appids, gamenames, folder_path, "positive", pos_counts, num_per_pages=100, max_pages=pos_pages, max_workers=max_workers)
    run(appids, gamenames, folder_path, "negative", neg_counts, num_per_pages=100, max_pages=neg_pages, max_workers=max_workers)
    merge_pos_neg(folder_path)
    
    output_file = f"total_{folder_name}_review{target_review_count}.csv"
    concat_merged_reviews(folder_path, output_file)


def main(target_review_count: int, target_game_count: int, max_workers: int) -> None:    
    process_reviews("toprated2000_plus_col.csv", "rated_top200", target_game_count, target_review_count, max_workers)
    process_reviews("topsell1100_plus_col.csv", "sellers_top200", target_game_count, target_review_count, max_workers)
    
    process_reviews("allgame_filt_10000.csv", "all_game", -1, target_review_count, max_workers)


if __name__ == "__main__":
    target_review_count = 200
    target_game_count = 200
    parallel_cpu_workers = 5
    
    main(target_review_count, target_game_count, parallel_cpu_workers)