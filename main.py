import os
import pandas as pd
from base_crawling import run_parallel_review_fetch as run
from constants import CSV_FOLDER_PATH, ENCODING_TYPE
from functions import merge_pos_neg, concat_merged_reviews, round_up_to_100


def get_appids_and_gamenames(file_name: str) -> tuple[list[int], list[int]]:
    df = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name), encoding=ENCODING_TYPE)
    return df['game_appid'].tolist(), df['game_name'].tolist()


def calculate_ratio(file_name: str, target_review_count: int) -> tuple[list[int], list[int]]:
    df = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name), encoding=ENCODING_TYPE)
    df['pos_count'] = df['eng_review_positive'] * target_review_count // 100
    df['neg_count'] = target_review_count - df['pos_count']
    return df['pos_count'].tolist(), df['neg_count'].tolist()


def process_reviews(file_name: str, folder_name: str, target_review_count: int, max_workers: int) -> None:
    appids, gamenames = get_appids_and_gamenames(file_name)
    pos_counts, neg_counts = calculate_ratio(file_name, target_review_count)
    pos_pages, neg_pages = map(round_up_to_100, pos_counts), map(round_up_to_100, neg_counts)
    folder_path = os.path.join("file", folder_name)
    
    print(f"[RUN] {folder_name} 리뷰 수집 시작({len(appids)}개 게임)")
    run(appids, gamenames, folder_path, "positive", pos_counts, num_per_pages=100, max_pages=pos_pages, max_workers=max_workers)
    run(appids, gamenames, folder_path, "negative", neg_counts, num_per_pages=100, max_pages=neg_pages, max_workers=max_workers)
    merge_pos_neg(folder_path)
    
    output_file = f"BRZ_review_{folder_name}_review{target_review_count}_final.csv"
    output_file = f"total_{folder_name}_review{target_review_count}.csv"
    concat_merged_reviews(folder_path, output_file)


def main(target_review_count: int, max_workers: int) -> None:    
    process_reviews("BRZ_meta_bothGames_reviewData_final.csv", "bothGames", target_review_count, max_workers)
    process_reviews("BRZ_meta_nonSuccess_reviewData_final.csv", "nonSuccess", target_review_count, max_workers)


if __name__ == "__main__":
    # target_game_count = 200
    target_review_count = 200
    parallel_cpu_workers = 5
    
    main(target_review_count, parallel_cpu_workers)