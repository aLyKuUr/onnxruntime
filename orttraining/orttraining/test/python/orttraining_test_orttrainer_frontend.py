import pytest
import torch
from numpy.testing import assert_allclose

from onnxruntime.capi.training import orttrainer_options as orttrainer_options
from onnxruntime.capi.training import orttrainer
from onnxruntime.capi.training import optim



@pytest.mark.parametrize("test_input", [
    ({}),
    ({'batch': {},
      'device': {},
      'distributed': {},
      'mixed_precision': {},
      'utils': {},
      '_internal_use': {}})
])
def testORTTrainerOptionsDefaultValues(test_input):
    ''' Test different ways of using default values for incomplete input'''

    expected_values = {
        'batch': {
            'gradient_accumulation_steps': 0
        },
        'device': {
            'id': None,
            'mem_limit': 0
        },
        'distributed': {
            'world_rank': 0,
            'world_size': 1,
            'local_rank': 0,
            'allreduce_post_accumulation': False,
            'enable_partition_optimizer': False,
            'enable_adasum': False
        },
        'lr_scheduler': None,
        'mixed_precision': {
            'enabled': False,
            'loss_scaler': None
        },
        'utils': {
            'grad_norm_clip': False
        },
        '_internal_use': {
            'frozen_weights': [],
            'enable_internal_postprocess': True,
            'extra_postprocess': None
        }
    }

    actual_values = orttrainer_options.ORTTrainerOptions(test_input)
    assert actual_values._validated_opts == expected_values


def testORTTrainerOptionsInvalidMixedPrecisionEnabledSchema():
    '''Test an invalid input based on schema validation error message'''

    expected_msg = "Invalid options: {'mixed_precision': [{'enabled': ['must be of boolean type']}]}"
    with pytest.raises(ValueError) as e:
        orttrainer_options.ORTTrainerOptions({'mixed_precision': {'enabled': 1}})
    assert str(e.value) == expected_msg


def testTrainStepInfo():
    '''Test valid initializations of TrainStepInfo'''

    step_info = orttrainer.TrainStepInfo(all_finite=True, epoch=1, step=2)
    assert step_info.all_finite is True
    assert step_info.epoch == 1
    assert step_info.step == 2

    step_info = orttrainer.TrainStepInfo()
    assert step_info.all_finite is None
    assert step_info.epoch is None
    assert step_info.step is None


@pytest.mark.parametrize("test_input", [
    (-1),
    ('Hello'),
])
def testTrainStepInfoInvalidAllFinite(test_input):
    '''Test invalid initialization of TrainStepInfo'''
    with pytest.raises(AssertionError):
        orttrainer.TrainStepInfo(all_finite=test_input)

    with pytest.raises(AssertionError):
        orttrainer.TrainStepInfo(epoch=test_input)

    with pytest.raises(AssertionError):
        orttrainer.TrainStepInfo(step=test_input)


@pytest.mark.parametrize("optim_name,lr,alpha,default_alpha", [
    ('AdamOptimizer', .1, .2, None),
    ('LambOptimizer', .2, .3, None),
    ('SGDOptimizer', .3, .4, None),
    ('SGDOptimizer', .3, .4, .5)
])
def testOptimizerConfig(optim_name, lr, alpha, default_alpha):
    '''Test initialization of _OptimizerConfig'''
    hyper_parameters = {'lr': lr, 'alpha': alpha}
    param_groups = [{'params': ['fc1.weight', 'fc2.weight']}]
    if default_alpha is not None:
        param_groups[0].update({'alpha': default_alpha})
    else:
        param_groups[0].update({'alpha': alpha})
    cfg = optim.config._OptimizerConfig(
        name=optim_name, hyper_parameters=hyper_parameters, param_groups=param_groups)

    assert cfg.name == optim_name
    rtol = 1e-03
    assert_allclose(hyper_parameters['lr'],
                    cfg.lr, rtol=rtol, err_msg="lr mismatch")

    # 1:1 mapping between hyper_parameters and param_groups's hyper parameters
    for group in param_groups:
        for k, _ in group.items():
            if k != 'params':
                assert k in cfg.hyper_parameters, "hyper parameter {k} not present in one of the parameter groups"
    for k, _ in cfg.hyper_parameters.items():
        for group in cfg.param_groups:
            assert k in group, "hyper parameter {k} not present in one of the parameter groups"


@pytest.mark.parametrize("optim_name,hyper_parameters,param_groups", [
    ('AdamOptimizer', {'lr': -1}, []),  # invalid lr
    ('FooOptimizer', {'lr': 0.001}, []),  # invalid name
    ('SGDOptimizer', [], []),  # invalid type(hyper_parameters)
    (optim.AdamConfig, {'lr': 0.003}, []),  # invalid type(name)
    ('AdamOptimizer', {'lr': None}, []),  # missing 'lr' hyper parameter
    ('SGDOptimizer', {'lr': 0.004}, {}),  # invalid type(param_groups)
    # invalid type(param_groups[i])
    ('AdamOptimizer', {'lr': 0.005, 'alpha': 2}, [[]]),
    # missing 'params' at 'param_groups'
    ('AdamOptimizer', {'lr': 0.005, 'alpha': 2}, [{'alpha': 1}]),
    # missing 'alpha' at 'hyper_parameters'
    ('AdamOptimizer', {'lr': 0.005}, [{'params': 'param1', 'alpha': 1}]),
])
def testOptimizerConfigInvalidInputs(optim_name, hyper_parameters, param_groups):
    '''Test invalid initialization of _OptimizerConfig'''

    with pytest.raises(AssertionError):
        optim.config._OptimizerConfig(
            name=optim_name, hyper_parameters=hyper_parameters, param_groups=param_groups)


def testSGDConfig():
    '''Test initialization of SGD'''
    cfg = optim.SGDConfig()
    assert cfg.name == 'SGDOptimizer'

    rtol = 1e-05
    assert_allclose(0.001, cfg.lr, rtol=rtol, err_msg="lr mismatch")

    cfg = optim.SGDConfig(lr=0.002)
    assert_allclose(0.002, cfg.lr, rtol=rtol, err_msg="lr mismatch")

    # SGD does not support param_groups
    with pytest.raises(AssertionError) as e:
        param_groups = [{'params': ['layer1.weight'], 'lr': 0.1}]
        optim.SGDConfig(param_groups=param_groups, lr=0.002)
        assert_allclose(0.002, cfg.lr, rtol=rtol, err_msg="lr mismatch")
    assert str(e.value) == "'param_groups' must be an empty list for SGD optimizer"


def testAdamConfig():
    '''Test initialization of Adam'''
    cfg = optim.AdamConfig()
    assert cfg.name == 'AdamOptimizer'

    rtol = 1e-05
    assert_allclose(0.001, cfg.lr, rtol=rtol, err_msg="lr mismatch")
    assert_allclose(0.9, cfg.alpha, rtol=rtol, err_msg="alpha mismatch")
    assert_allclose(0.999, cfg.beta, rtol=rtol, err_msg="beta mismatch")
    assert_allclose(0.0, cfg.lambda_coef, rtol=rtol,
                    err_msg="lambda_coef mismatch")
    assert_allclose(1e-8, cfg.epsilon, rtol=rtol, err_msg="epsilon mismatch")
    assert cfg.do_bias_correction == True, "lambda_coef mismatch"
    assert cfg.weight_decay_mode == True, "weight_decay_mode mismatch"


def testLambConfig():
    '''Test initialization of Lamb'''
    cfg = optim.LambConfig()
    assert cfg.name == 'LambOptimizer'
    rtol = 1e-05
    assert_allclose(0.001, cfg.lr, rtol=rtol, err_msg="lr mismatch")
    assert_allclose(0.9, cfg.alpha, rtol=rtol, err_msg="alpha mismatch")
    assert_allclose(0.999, cfg.beta, rtol=rtol, err_msg="beta mismatch")
    assert_allclose(0.0, cfg.lambda_coef, rtol=rtol,
                    err_msg="lambda_coef mismatch")
    assert cfg.ratio_min == float('-inf'), "ratio_min mismatch"
    assert cfg.ratio_max == float('inf'), "ratio_max mismatch"
    assert_allclose(1e-6, cfg.epsilon, rtol=rtol, err_msg="epsilon mismatch")
    assert cfg.do_bias_correction == True, "lambda_coef mismatch"


@pytest.mark.parametrize("optim_name", [
    ('Adam'),
    ('Lamb')
])
def testParamGroups(optim_name):
    rtol = 1e-5
    param_groups = [{'params': ['layer1.weight'], 'alpha': 0.1}]
    if optim_name == 'Adam':
        cfg = optim.AdamConfig(param_groups=param_groups, alpha=0.2)
    elif optim_name == 'Lamb':
        cfg = optim.LambConfig(param_groups=param_groups, alpha=0.2)
    else:
        raise ValueError('invalid input')
    assert len(cfg.param_groups) == 1, "param_groups should have length 1"
    assert_allclose(cfg.param_groups[0]['alpha'], 0.1,
                    rtol=rtol, err_msg="invalid lr on param_groups[0]")


@pytest.mark.parametrize("optim_name", [
    ('Adam'),
    ('Lamb')
])
def testInvalidParamGroups(optim_name):
    # lr is not supported within param_groups
    with pytest.raises(AssertionError) as e:
        param_groups = [{'params': ['layer1.weight'], 'lr': 0.1}]
        if optim_name == 'Adam':
            optim.AdamConfig(param_groups=param_groups, lr=0.2)
        elif optim_name == 'Lamb':
            optim.LambConfig(param_groups=param_groups, lr=0.2)
        else:
            raise ValueError('invalid input')
    assert str(e.value) == "'lr' is not supported inside param_groups"

