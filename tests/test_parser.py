import pytest
from parser.sas_parser import SASParser
from models.step import StepType


def test_parse_sample_etl():
    parser = SASParser()
    sas_code = """
    DATA work.out;
        SET work.in;
        WHERE age >= 18;
    RUN;
    """
    steps = parser.parse_script(sas_code)

    assert len(steps) == 1
    assert steps[0].step_type == StepType.DATA_STEP
    assert "work.out" in steps[0].output_datasets
    assert "work.in" in steps[0].input_datasets
