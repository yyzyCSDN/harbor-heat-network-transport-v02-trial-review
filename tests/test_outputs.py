"""Public thermal-contract behaviors with independently frozen expected values."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_output import verify
from runner import run_cases

CASES=json.loads((Path(__file__).parent/'cases.json').read_text(encoding='utf-8'))
EXPECTED={row['id']:row['expected'] for row in CASES}

@pytest.fixture(scope='session')
def results():
    return run_cases(CASES,verify)

def test_layered_forward_interfaces(results):
    'instruction.md — 初态分层；t=0流动取上游侧，初始界面与入口交接'
    row=results['layered_forward_interfaces']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['layered_forward_interfaces']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_layered_reverse_interfaces(results):
    'instruction.md — 负流初态界面、固定端点与源端切换'
    row=results['layered_reverse_interfaces']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['layered_reverse_interfaces']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_stagnant_spatial_traces(results):
    'instruction.md — 停流空间右迹、末端左迹、孤立节点null、重复乱序'
    row=results['stagnant_spatial_traces']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['stagnant_spatial_traces']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_acceleration_residence_history(results):
    'instruction.md — 流量加速后的累计位移与真实年龄，不能用当前固定延迟'
    row=results['acceleration_residence_history']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['acceleration_residence_history']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_deceleration_residence_history(results):
    'instruction.md — 减速保留温度前沿，时延横跨控制区间'
    row=results['deceleration_residence_history']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['deceleration_residence_history']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_stall_then_restart(results):
    'instruction.md — 停流阶段散热和重启前沿年龄，节点为空不等于管内无状态'
    row=results['stall_then_restart']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['stall_then_restart']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_same_end_return(results):
    'instruction.md — 反转后此前进入的水从同端返回，新控制瞬间不沿用旧端口缓存'
    row=results['same_end_return']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['same_end_return']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_multiple_reversals(results):
    'instruction.md — 多次反转和不同速率，未排出的分层必须保留'
    row=results['multiple_reversals']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['multiple_reversals']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_stop_reverse_restart(results):
    'instruction.md — 停流与反向重启、停流节点温度不施加到管内'
    row=results['stop_reverse_restart']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['stop_reverse_restart']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_front_and_reversal_coincide(results):
    'instruction.md — 前沿到达与反转同刻；右极限按新方向选择管内迹'
    row=results['front_and_reversal_coincide']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['front_and_reversal_coincide']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_source_sink_at_stopped_nodes(results):
    'instruction.md — 节点外源外汇仍可混合，停止管端保持内部状态'
    row=results['source_sink_at_stopped_nodes']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['source_sink_at_stopped_nodes']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_unequal_incoming_mix(results):
    'instruction.md — 两支路以2:1混合并部分取水，剩余出流继续输运'
    row=results['unequal_incoming_mix']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['unequal_incoming_mix']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_external_source_recirculation(results):
    'instruction.md — 外源与闭环回流混合，有限驻留导致带记忆递推'
    row=results['external_source_recirculation']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['external_source_recirculation']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_split_merge_chain(results):
    'instruction.md — 分流后不同路径再汇流，六节点且管序不按拓扑排列'
    row=results['split_merge_chain']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['split_merge_chain']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_parallel_delays_and_losses(results):
    'instruction.md — 并行管保留不同停留时间与损耗，节点按实际流量混合'
    row=results['parallel_delays_and_losses']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['parallel_delays_and_losses']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_closed_ring_initial_memory(results):
    'instruction.md — 无外源闭环，初态沿环转动并按所经管段损耗'
    row=results['closed_ring_initial_memory']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['closed_ring_initial_memory']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_source_ring_delayed_recurrence(results):
    'instruction.md — 常外源闭环的递推而非瞬时全网均温'
    row=results['source_ring_delayed_recurrence']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['source_ring_delayed_recurrence']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_two_incoming_cycles(results):
    'instruction.md — 每节点两条入流管的分叉回溯，热历史不可压成单一延迟'
    row=results['two_incoming_cycles']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['two_incoming_cycles']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_whole_ring_reverse_stall(results):
    'instruction.md — 闭环反转、整体停流和重启，新节点混合来自当前剖面'
    row=results['whole_ring_reverse_stall']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['whole_ring_reverse_stall']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_disconnected_and_isolated(results):
    'instruction.md — 多个组件、停流组件及孤立节点无虚假混合'
    row=results['disconnected_and_isolated']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['disconnected_and_isolated']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_heterogeneous_loss_chain(results):
    'instruction.md — 多管串联各自损耗和实际历史，不能总用一种衰减率'
    row=results['heterogeneous_loss_chain']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['heterogeneous_loss_chain']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_zero_and_tiny_loss(results):
    'instruction.md — 零与极小loss的指数积分稳定性，避免相消或除零'
    row=results['zero_and_tiny_loss']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['zero_and_tiny_loss']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_negative_relative_heat(results):
    'instruction.md — 低于环境的加热过程及负相对蓄热不能截断为0'
    row=results['negative_relative_heat']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['negative_relative_heat']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_nonuniform_remaining_heat(results):
    'instruction.md — 分层部分排出后剩余热量，均温储罐不能代替塞流'
    row=results['nonuniform_remaining_heat']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['nonuniform_remaining_heat']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_query_order_and_repetition(results):
    'instruction.md — 乱序重复查询不改变历史，重复位置必须一致'
    row=results['query_order_and_repetition']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['query_order_and_repetition']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_simultaneous_port_role_changes(results):
    'instruction.md — 同刻一管停流另一管反转，节点入流集合必须重新选择'
    row=results['simultaneous_port_role_changes']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['simultaneous_port_role_changes']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_initial_and_final_control(results):
    'instruction.md — t=0边界及t=6最后控制，新控制必须延续到查询右侧'
    row=results['initial_and_final_control']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['initial_and_final_control']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_maximum_shape_with_components(results):
    'instruction.md — 最大6节点8管6控制12查询16探针；维度不冒称最难搜索'
    row=results['maximum_shape_with_components']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['maximum_shape_with_components']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3

def test_fast_branching_reversal_combo(results):
    'instruction.md — 最短全穿越时间、双入流、异损耗及密集反转组合'
    row=results['fast_branching_reversal_combo']
    assert row['returncode']==0, row['errors']
    assert row['output'] is not None, row['errors']
    assert row['errors']==[], '\n'.join(row['errors'])
    snapshots=row['output']['snapshots']
    expected=EXPECTED['fast_branching_reversal_combo']['snapshots']
    assert len(snapshots)==len(expected)
    for actual,goal in zip(snapshots,expected):
        assert actual['time']==goal['time']
        assert len(actual['nodes'])==len(goal['nodes'])
        assert len(actual['probes'])==len(goal['probes'])
        assert len(actual['pipe_heat'])==len(goal['pipe_heat'])
        for value,target in zip(actual['nodes'],goal['nodes']):
            if target is None:
                assert value is None
            else:
                assert abs(value-target)<=5e-5
        for value,target in zip(actual['probes'],goal['probes']):
            assert abs(value-target)<=5e-5
        for value,target in zip(actual['pipe_heat'],goal['pipe_heat']):
            assert abs(value-target)<=2e-3
