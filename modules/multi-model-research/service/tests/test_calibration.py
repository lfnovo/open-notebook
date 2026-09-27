"""A margin is only calibrated by measurements that are actually single-message."""
import pytest

from calibration import Observation, admissible, check_margin, fit_margin, observations


def obs(raw, reported, attempts=1, tool_calls=0, stage='synthesis_chatgpt', provider='ChatGPT'):
    return Observation(run='r', stage=stage, provider=provider, raw_tokens=raw,
                       reported_tokens=reported, attempts=attempts, tool_calls=tool_calls,
                       profile='research_synthesis', runtime_fingerprint='measured-runtime',measurement_kind='single_context',representation='serialized_input')


def test_multi_attempt_usage_is_not_a_tokenizer_measurement():
    assert admissible(obs(1000, 1200)) is True
    assert admissible(obs(1000, 4800, attempts=2)) is False


def test_tool_using_stages_are_not_admissible():
    """Preliminary research aggregates an agent loop; its prompt_tokens is not one prompt."""
    assert admissible(obs(1801, 3_023_277, tool_calls=37)) is False


def test_fit_bounds_every_measurement_from_above():
    points = [obs(46258, 57823), obs(80092, 94739), obs(111075, 126661), obs(137110, 160991)]
    margin = fit_margin(points)
    for point in points:
        assert margin['multiplier'] * point.raw_tokens + margin['overhead_tokens'] >= point.reported_tokens


def test_fit_refuses_a_single_point_without_a_declared_floor():
    with pytest.raises(ValueError):
        fit_margin([obs(80092, 142873, provider='Claude')])


def test_fit_accepts_a_single_point_when_the_slope_is_declared():
    margin = fit_margin([obs(80092, 142873, provider='Claude')], assumed_multiplier=1.8)
    assert margin['multiplier'] == 1.8
    assert 1.8 * 80092 + margin['overhead_tokens'] >= 142873
    assert margin['points'] == 1


def test_check_margin_finds_underestimates():
    """The failure that matters: an estimate below the truth lets an oversized packet through."""
    points = [obs(80092, 94739), obs(137110, 160991)]
    report = check_margin({'multiplier': 1.0, 'overhead_tokens': 15489}, points)
    assert report['unsafe'] is True
    assert report['worst_shortfall'] == 160991 - (137110 + 15489)
    assert [p['stage'] for p in report['underestimated']] == ['synthesis_chatgpt']


def test_check_margin_accepts_a_bounding_margin():
    points = [obs(80092, 94739), obs(137110, 160991)]
    report = check_margin(fit_margin(points + [obs(46258, 57823)]), points)
    assert report['unsafe'] is False
    assert report['underestimated'] == []


def test_fit_keeps_a_flat_reserve_above_the_tightest_line():
    points = [obs(46258, 57823), obs(80092, 94739), obs(137110, 160991)]
    tight = fit_margin(points, reserve_tokens=0)
    assert fit_margin(points, reserve_tokens=2048)['overhead_tokens'] == tight['overhead_tokens'] + 2048


def test_the_reserve_does_not_scale_with_packet_size():
    """A percentage reserve would charge twice for the conservatism already in the multiplier."""
    small = fit_margin([obs(1000, 1250), obs(2000, 2400)])
    large = fit_margin([obs(100000, 125000), obs(200000, 240000)])
    assert small['overhead_tokens'] == large['overhead_tokens']


def test_overhead_compensates_a_declared_multiplier_below_the_observed_ratio():
    """With a flat slope the constant term is what keeps the fit above the data."""
    points = [obs(80092, 142873, provider='Claude'), obs(20000, 30000, provider='Claude')]
    margin = fit_margin(points, assumed_multiplier=1.2, reserve_tokens=0)
    assert margin['multiplier'] == 1.2
    for point in points:
        assert 1.2 * point.raw_tokens + margin['overhead_tokens'] >= point.reported_tokens
    assert margin['overhead_tokens'] >= 142873 - 1.2 * 80092


def test_unknown_measurement_shape_is_not_silently_assumed_safe():
    from dataclasses import replace
    assert not admissible(replace(obs(1000,1200),measurement_kind='unknown'))
    assert not admissible(replace(obs(1000,1200),representation='prompt_only'))
    assert not admissible(replace(obs(1000,1200),profile='preliminary_merge'))
    assert not admissible(replace(obs(1000,1200),runtime_fingerprint=None))


def test_runtime_or_provider_changes_cannot_be_combined():
    from dataclasses import replace
    with pytest.raises(ValueError):fit_margin([obs(1000,1200),replace(obs(2000,2300),runtime_fingerprint='other')])
    with pytest.raises(ValueError):fit_margin([obs(1000,1200),obs(2000,2300,provider='Claude')])


@pytest.mark.parametrize('value',[float('nan'),float('inf'),.9,-1])
def test_invalid_margin_parameters_are_rejected(value):
    with pytest.raises(ValueError):fit_margin([obs(1000,1200)],assumed_multiplier=value)


def recorded(usage, status='completed'):
    stage={'id':'synthesis_claude','provider':'Claude','mode':'account','status':status,
           'attempts':1,'account_profile':'research_synthesis','usage':usage,
           'input_budget':{'token_margin':{'calibration_fingerprint':'runtime'}}}
    return observations([{'id':'run','stages':[stage]}],lambda *_:1000)[0]


def test_legacy_partial_iteration_count_is_not_single_context_proof():
    point=recorded({'prompt_tokens':3000,'first_context_tokens':2000,'context_observations':1})
    assert point.measurement_kind=='unknown'
    assert not admissible(point)


@pytest.mark.parametrize('patch',[
    {'context_observations_complete':False}, {'cli_num_turns':2},
    {'context_observations':2}, {'cli_num_turns':True}, {'context_observations':True},
    {'context_observations_complete':'true'},
])
def test_incomplete_or_multi_turn_measurements_cannot_calibrate(patch):
    usage={'prompt_tokens':1200,'first_context_tokens':1200,'context_observations':1,
           'context_observations_complete':True,'cli_num_turns':1}
    assert not admissible(recorded(usage|patch))


def test_only_completed_proven_single_context_is_admitted():
    usage={'prompt_tokens':1200,'first_context_tokens':1200,'context_observations':1,
           'context_observations_complete':True,'cli_num_turns':1}
    assert admissible(recorded(usage))
    assert not admissible(recorded(usage,status='blocked'))
