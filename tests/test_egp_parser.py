import pytest
from pathlib import Path
from sas2pyspark.parsers.egp_parser import EGPParser


def test_parse_egp_dir():
    egp_dir = Path("/home/abhishek/sas-to-pyspark-convertor-agent/NetflixHistory43")
    if not egp_dir.exists():
        pytest.skip("NetflixHistory43 directory not present")

    parser = EGPParser()
    flow = parser.parse(str(egp_dir))

    assert flow.id is not None
    assert len(flow.nodes) > 0
    assert len(flow.execution_order) > 0


def test_parse_egp_file():
    egp_file = Path("/home/abhishek/sas-to-pyspark-convertor-agent/NetflixHistory43.egp")
    if not egp_file.exists():
        pytest.skip("NetflixHistory43.egp file not present")

    parser = EGPParser()
    flow = parser.parse(str(egp_file))

    assert flow.name == "NetflixHistory43"
    assert len(flow.nodes) > 0
