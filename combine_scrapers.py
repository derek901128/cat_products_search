from pathlib import Path
from scrapers.site_one import scrape_site_one
from scrapers.site_two import scrape_site_two
from scrapers.site_three import scrape_site_three
from scrapers.site_four import scrape_site_four
import dotenv
import boto3
import duckdb
import time

def main():
    start = time.perf_counter()
    config = dotenv.dotenv_values('.env')
    conn = duckdb.connect(config['DB'])

    site_one_products = scrape_site_one()
    site_two_products = scrape_site_two()
    site_three_products = scrape_site_three()
    site_four_products = scrape_site_four()

    s3 = boto3.resource(
        's3',
        region_name=config['REGION'],
        aws_access_key_id=config['AWS_KEY'],
        aws_secret_access_key=config['AWS_SECRET_KEY']
    )

    for log in Path('.').glob('*.log'):
        s3.Bucket(config['BUCKET']).upload_file(Filename=log, Key=log.as_posix())
        print(f"Log for {log} is uploaded to S3!")
        log.unlink()

    conn.execute("""
        drop table if exists site_one_products;
        create table site_one_products as
            select
                * exclude(flavors)
                , '口味： ' || flavors as extra_info
            from
                site_one_products
        ;
    """)

    print("Table created for site one!")

    conn.execute("""
        drop table if exists site_two_products;
        create table site_two_products as
            select
                *
                , case
                    trim(regexp_extract(names, '【(.*?)】', 1))
                    when ''
                    then ''
                    else '製造商：' || trim(regexp_extract(names, '【(.*?)】', 1))
                    end as extra_info
            from
                site_two_products;
    """)

    print("Table created for site two!")

    conn.execute("""
        drop table if exists site_three_products;
        create table site_three_products as
            select
                * exclude(manufacturer_names, prices)
                , regexp_extract(prices, 'HK\$([1-9]+,)?[0-9]+\.[0-9]+') as prices
                , regexp_extract(lower(names), '\d{1,}(\.\d{1,})?(kg|g|ml|l|克|粒|磅|oz)') as weights
                , '製造商： ' || manufacturer_names || '; 優惠： ' || regexp_extract(prices, '0([1-9]{1,}件.*)', 1) as extra_info
            from
                site_three_products;
    """)

    print("Table created for site three!")

    conn.execute("""
        drop table if exists site_four_products;
        create table site_four_products as
            select
                *
                exclude(categories)
                , '分類： ' || categories  as extra_info
            from
                site_four_products;
    """)

    print("Table created for site four!")

    conn.execute("""
        drop table if exists all_cat_products;
        create table all_cat_products as
            select
                sitenames
                , names
                , weights
                , prices
                , extra_info
                , links
                , current_date as last_updated
            from
                site_one_products
            union all
            select
                sitenames
                , names
                , weights
                , prices
                , extra_info
                , links
                , current_date as last_updated
            from
                site_two_products
            union all
            select
                sitenames
                , names
                , weights
                , prices
                , extra_info
                , links
                , current_date as last_updated
            from
                site_three_products
            union all
            select
                sitenames
                , names
                , weights
                , prices
                , extra_info
                , links
                , current_date as last_updated
            from
                site_four_products;
    """)

    rows_inserted = conn.sql("""
        select count(*) from all_cat_products;
    """).fetchall()[0][0]

    conn.close()

    end = time.perf_counter()

    print("\n****************************************************************************************************************************\n")
    print(f"All sites fetched! Rows fetched and inserted: {rows_inserted}. Time used: {end - start} s")
    print("\n****************************************************************************************************************************\n")

if __name__ == "__main__":
    main()