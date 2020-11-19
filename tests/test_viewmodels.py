import pytest
from seller_stats.category_stats import CategoryStats

from src.viewmodels.report import Report


@pytest.fixture()
def report_vm_from_source_file(scrapinghub_dataset):
    def _report_vm_from_source_file(job_id, result_source):
        data = scrapinghub_dataset(job_id=job_id, result_source=result_source)
        stats = CategoryStats(data=data)

        return Report(stats=stats, username='username')

    return _report_vm_from_source_file


def test_corrupted_chart_handling(report_vm_from_source_file):
    report_vm = report_vm_from_source_file(job_id='123/1/2', result_source='wb_corrupted_charts_raw')

    report_vm.to_dict()

    assert True  # assert there is no exception
