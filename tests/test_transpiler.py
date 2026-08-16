import pytest
from sas2pyspark.models import SASCodeBlock, BlockType
from sas2pyspark.agent import SAS2PySparkAgent


def test_transpile_proc_sort():
    agent = SAS2PySparkAgent()
    block = SASCodeBlock(
        id="b1",
        block_type=BlockType.PROC_SORT,
        input_datasets=["work.movies"],
        output_datasets=["work.movies_sorted"],
        raw_code="PROC SORT DATA=work.movies OUT=work.movies_sorted NODUPKEY; BY title DESCENDING rating; RUN;"
    )

    conv = agent.convert_block(block)
    assert "work_movies_sorted = work_movies.sort" in conv.pyspark_code
    assert 'F.col("title").asc()' in conv.pyspark_code
    assert 'F.col("rating").desc()' in conv.pyspark_code
    assert "dropDuplicates" in conv.pyspark_code


def test_transpile_proc_sql():
    agent = SAS2PySparkAgent()
    block = SASCodeBlock(
        id="b2",
        block_type=BlockType.PROC_SQL,
        input_datasets=["work.ratings"],
        output_datasets=["work.summary"],
        raw_code="PROC SQL; CREATE TABLE work.summary AS SELECT rating, COUNT(*) FROM work.ratings GROUP BY rating; QUIT;"
    )

    conv = agent.convert_block(block)
    assert "work_summary = spark.sql(" in conv.pyspark_code
    assert 'createOrReplaceTempView("work_summary")' in conv.pyspark_code


def test_transpile_data_step_merge_by():
    agent = SAS2PySparkAgent()
    block = SASCodeBlock(
        id="b3",
        block_type=BlockType.DATA_STEP,
        input_datasets=["work.ds1", "work.ds2"],
        output_datasets=["work.merged"],
        raw_code="DATA work.merged; MERGE work.ds1 work.ds2; BY customer_id; RUN;"
    )

    conv = agent.convert_block(block)
    assert 'work_merged = work_ds1.join(work_ds2, on=["customer_id"], how="full_outer")' in conv.pyspark_code
    assert 'work_merged.createOrReplaceTempView("work_merged")' in conv.pyspark_code


def test_transpile_proc_format():
    agent = SAS2PySparkAgent()
    block = SASCodeBlock(
        id="b4",
        block_type=BlockType.PROC_FORMAT,
        input_datasets=[],
        output_datasets=[],
        raw_code="PROC FORMAT; VALUE rating 1='Poor' 2='Good' OTHER='Unknown'; RUN;"
    )

    conv = agent.convert_block(block)
    assert "def apply_rating_format(col_expr):" in conv.pyspark_code
    assert '.when(col_expr == 1, "Poor")' in conv.pyspark_code
    assert '.otherwise("Unknown")' in conv.pyspark_code
