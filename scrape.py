import argparse
import psycopg2

from datetime import datetime

from apis import main as main_apis
from scraper import main as main_scraper

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="run scraping in headless mode",
    )
    parser.add_argument(
        "--push-to-db",
        action="store_true",
        default=False,
        help="push the scraped results to db",
    )
    args = parser.parse_args()

    df = main_scraper(headless=args.headless)
    # df2 = main_apis()

    # df = df1 + df2

    dt = datetime.now()
    insert_time = dt.strftime("%Y%m%d_%H%M%S")
    with open(f"results/events_{insert_time}.json", "w", encoding="UTF-8") as file:
        df.to_json(file, orient="records", force_ascii=False)

    if args.push_to_db:
        print("Pushing scraped results into db...")
        credentials = get_config()
        host = credentials["host"]
        port = credentials["port"]
        user = credentials["user"]
        psw = credentials["psw"]
        database = credentials["database"]

        conn = psycopg2.connect(
            database=database, user=user, password=psw, host=host, port=port
        )

        etl(conn, df)
        print("Done")

        conn.close()
