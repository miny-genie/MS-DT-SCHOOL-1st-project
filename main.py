import os
import pandas as pd
from base_crawling import run_parallel_review_fetch as run
from constants import CSV_FOLDER_PATH


def get_appids_and_gamenames(file_name: str) -> list[int]:
    # std_df = pd.read_csv(os.path.join(CSV_FOLDER_PATH , file_name))
    # appid_df = pd.read_csv(os.path.join(CSV_FOLDER_PATH , "appid.csv"))
    
    # df = pd.merge(
    #     std_df,
    #     appid_df[['appid', '게임명']],
    #     how="left",
    #     left_on='게임이름', 
    #     right_on='게임명'
    # )
    df = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name))
    return df['app_id'].tolist(), df['게임이름'].tolist()


def calculate_ratio(file_name: str, target_review_count: int) -> tuple[int]:
    std_df = pd.read_csv(os.path.join(CSV_FOLDER_PATH, file_name))
    std_df['pos_count'] = std_df['긍정적인 평가 비율'] * target_review_count // 100
    std_df['neg_count'] = (100 - std_df['긍정적인 평가 비율']) * target_review_count // 100
    return std_df['pos_count'].tolist(), std_df['neg_count'].tolist()


def main():
    target_review_count = 500
    target_game_count = 200
    max_workers = 5

    # TOP RATED: set argument
    rate_file_name = "toprated2000_plus_col.csv"
    rate_appids, rate_gamenames = get_appids_and_gamenames(rate_file_name)
    rate_folder = "file/top_rated_200"
    pos_counts, neg_counts = calculate_ratio(rate_file_name, target_review_count)  # 비율에 따른 리뷰 수집을 위한 계산

    rate_appids = rate_appids[:target_game_count]
    rate_gamenames = rate_gamenames[:target_game_count]
    pos_counts = pos_counts[:target_game_count]
    neg_counts = neg_counts[:target_game_count]

    # TOP RATED: start crawling
    print(f"[RUN] Top rated {len(rate_appids)} steam game review crawling")
    run(appids=rate_appids, game_names=rate_gamenames, path=rate_folder, review_type="positive", ratio_counts=pos_counts, num_per_pages=100, max_pages=5, max_workers=max_workers)
    run(appids=rate_appids, game_names=rate_gamenames, path=rate_folder, review_type="negative", ratio_counts=neg_counts, num_per_pages=100, max_pages=5, max_workers=max_workers)
    
    # TOP SELLER: set argument
    seller_file_name = "topsell1100_plus_col.csv"
    seller_appids, seller_gamenames = get_appids_and_gamenames(seller_file_name)
    seller_folder = "file/top_sellers_200"
    pos_counts, neg_counts = calculate_ratio(rate_file_name, target_review_count)  # 비율에 따른 리뷰 수집을 위한 계산

    seller_appids = seller_appids[:target_game_count]
    seller_gamenames = seller_gamenames[:target_game_count]
    pos_counts = pos_counts[:target_game_count]
    neg_counts = neg_counts[:target_game_count]

    # TOP SELLER: start crawling
    print(f"[RUN] Top rated {len(seller_appids)} steam game review crawling")
    run(appids=seller_appids, game_names=seller_gamenames, path=seller_folder, review_type="positive", ratio_counts=pos_counts, num_per_pages=100, max_pages=5, max_workers=max_workers)
    run(appids=seller_appids, game_names=seller_gamenames, path=seller_folder, review_type="negative", ratio_counts=neg_counts, num_per_pages=100, max_pages=5, max_workers=max_workers)


if __name__ == "__main__":
    main()