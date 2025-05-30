import os
import pandas as pd
import glob


def merge(folder: str, file_names: str) -> None:
    rate_files = glob.glob(f"{folder}/{file_names}")

    all_dfs = []
    for file in rate_files:
        try:
            # app_id 추출 (파일명에서 숫자만 추출)
            app_id = os.path.splitext(os.path.basename(file))[0].split("_")[1]
            # csv 읽고 app_id 컬럼 추가
            df = pd.read_csv(file)
            df["app_id"] = int(app_id)
            
            # 리스트에 추가
            all_dfs.append(df)
        
        except Exception as e:
            print(f"[{app_id}] {e}")

    merged_df = pd.concat(all_dfs, ignore_index=True)
    merged_df.to_csv(f"all_{folder}_reviews.csv", index=False, encoding="utf-8-sig")

    print(f"✅ 총 {len(merged_df)}개 리뷰가 'all_reviews.csv'로 저장되었습니다.")
    return


if __name__ == "__main__":
    merge(folder="top_rated_200", file_names="review_*.csv")
    merge(folder="top_sellers_200", file_names="review_*.csv")