import pytest
from sas2pyspark.parsers.sas_parser import SASParser
from sas2pyspark.models import BlockType


def test_parse_data_step():
    sas_code = """
    DATA work.netflix_clean;
        SET work.netflix_raw;
        WHERE rating != '';
        title_upper = UPCASE(dvd_title);
        year_viewed = YEAR(shipped);
    RUN;
    """
    parser = SASParser()
    blocks = parser.parse_script(sas_code)

    assert len(blocks) == 1
    b = blocks[0]
    assert b.block_type == BlockType.DATA_STEP
    assert "work.netflix_clean" in b.output_datasets
    assert "work.netflix_raw" in b.input_datasets


def test_parse_proc_sql():
    sas_code = """
    PROC SQL;
        CREATE TABLE work.top_titles AS
        SELECT dvd_title, COUNT(*) AS view_count
        FROM work.netflix_clean
        GROUP BY dvd_title
        ORDER BY view_count DESC;
    QUIT;
    """
    parser = SASParser()
    blocks = parser.parse_script(sas_code)

    assert len(blocks) == 1
    b = blocks[0]
    assert b.block_type == BlockType.PROC_SQL
    assert "work.top_titles" in b.output_datasets
    assert "work.netflix_clean" in b.input_datasets
