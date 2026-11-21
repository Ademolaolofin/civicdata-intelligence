from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/dfe/eyfs_headline_measures_child_characteristics_2024_25.csv'
OUTPUT = ROOT / 'data/processed/lof_dfe_eyfs_observations.csv'
GLD = 'lof_metric_dbd49799b5ab'
FSM = 'lof_metric_c7904d3d7fa2'
ELIGIBLE = 'Eligible for free school meals'
NOT_ELIGIBLE = 'Not eligible for free school meals'

@pytest.fixture(scope='module')
def records():
    if not RAW.exists() or not OUTPUT.exists():
        pytest.skip('Run the DfE download and ingestion locally before testing.')
    raw = pd.read_csv(RAW, low_memory=False, dtype={'new_la_code':str, 'lad_code':str})
    output = pd.read_csv(OUTPUT, dtype={'authority_code':str})
    raw = raw.loc[raw['geographic_level'].isin(['Local authority','Local authority district'])].copy()
    raw['authority_code'] = raw['new_la_code'].where(raw['geographic_level'].eq('Local authority'),raw['lad_code'])
    raw['value_numeric'] = pd.to_numeric(raw['gld_children_percent'], errors='coerce')
    return raw, output

def test_unique_keys_and_expected_metrics(records):
    _, out = records
    assert set(out['metric_id']) == {GLD,FSM}
    assert not out.duplicated(['metric_id','authority_code','time_period']).any()
    assert out['period'].notna().all()
    assert out['source_geography'].isin(['Local authority','Local authority district']).all()

def test_geography_priority_and_values(records):
    raw, out = records
    for metric, topic, categories in [
        (GLD,'Total',['Total']),
        (FSM,'Free school meal eligibility',[ELIGIBLE,NOT_ELIGIBLE]),
    ]:
        src = raw.loc[(raw['breakdown_topic']==topic)&raw['breakdown'].isin(categories)&raw['sex'].eq('Total')].copy()
        src = src.loc[src['authority_code'].isin(out['authority_code'])]
        src['priority'] = src['geographic_level'].map({'Local authority':0,'Local authority district':1})
        keys = ['authority_code','time_period','breakdown']
        assert not src.duplicated(keys+['geographic_level']).any(), 'Duplicate source components'
        selected = src.sort_values(keys+['priority']).drop_duplicates(keys)
        if metric == GLD:
            expected = selected[['authority_code','time_period','geographic_level','value_numeric']].rename(columns={'geographic_level':'expected_geography','value_numeric':'expected_value'})
        else:
            geo = selected.groupby(['authority_code','time_period'])['geographic_level'].nunique()
            assert (geo <= 1).all(), 'FSM components were selected from different geography levels'
            expected = selected.pivot(index=['authority_code','time_period'],columns='breakdown',values='value_numeric').reset_index()
            expected['expected_value'] = expected[NOT_ELIGIBLE]-expected[ELIGIBLE]
            expected_geo = selected.drop_duplicates(['authority_code','time_period'])[['authority_code','time_period','geographic_level']].rename(columns={'geographic_level':'expected_geography'})
            expected = expected.merge(expected_geo,on=['authority_code','time_period'],validate='one_to_one')
        actual = out.loc[out['metric_id'].eq(metric)].merge(expected,on=['authority_code','time_period'],how='left',validate='one_to_one',indicator=True)
        assert actual['_merge'].eq('both').all(), 'Output includes unmatched source keys'
        assert actual['source_geography'].eq(actual['expected_geography']).all(), 'Geography priority mismatch'
        pd.testing.assert_series_equal(pd.to_numeric(actual['value'],errors='coerce').reset_index(drop=True),actual['expected_value'].reset_index(drop=True),check_names=False,check_exact=False,rtol=1e-9,atol=1e-8)
        if metric == FSM:
            for col,source_col in [('component_eligible_fsm_pct',ELIGIBLE),('component_not_eligible_fsm_pct',NOT_ELIGIBLE)]:
                pd.testing.assert_series_equal(pd.to_numeric(actual[col],errors='coerce').reset_index(drop=True),actual[source_col].reset_index(drop=True),check_names=False,check_exact=False,rtol=1e-9,atol=1e-8)

def test_missing_fsm_values(records):
    _, out = records
    missing = out.loc[out['metric_id'].eq(FSM)&out['value'].isna()]
    assert set(missing['authority_code']) == {'E06000053'}
    assert len(missing) == 4
