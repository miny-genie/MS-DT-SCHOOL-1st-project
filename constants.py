import os

STEAM_API_KEY = "3B317350A8372FDFDFA237479C5DA655"
STEAM_ID = "76561198150410975"
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
CSV_FOLDER_PATH = os.path.join(ROOT_PATH, 'file')
ENCODING_TYPE = 'utf-8-sig'
DTYPE_MAP = {
    "game_appid": "str",
    "game_name": "str",
    "review_id": "str",
    "author_steam_id": "str",
    "author_num_games_owned": "Int64",
    "author_reviews_count": "Int64",
    "author_playtime_forever": "Int64",
    "author_playtime_last_two_week": "Int64",
    "author_playtime_at_review": "Int64",
    "author_last_played_time": "str",
    "review_language": "str",
    "review_text": "str",
    "review_created_time": "str",
    "review_updated_time": "str",
    "b_game_recommendation": "boolean",
    "review_recommendation_count": "Int64",
    "review_funny_count": "Int64",
    "review_weighted_rating_score": "float",
    "review_comment_count": "Int64",
    "b_author_steam_purchase": "boolean",
    "b_author_received_for_free": "boolean",
    "b_review_written_during_early_access": "boolean",
    "b_primarily_steam_deck": "boolean"
}