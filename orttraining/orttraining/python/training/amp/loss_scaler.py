class LossScaler(object):
    r"""Base class for implementing custom loss scaler strategies

    Once the scaler is configured, no user intervention is needed to update loss scale during training.

    Note:
        This class should never be instantiated, but used as an abstract class for custom loss scaling strategy.
    """
    def __init__(self):
        pass

    def reset(self):
        r"""Resets loss scaler internal state"""
        raise NotImplementedError

    def update(self, train_step_info):
        r"""Updates loss based on user input and training session info

        Args:
            train_step_info (TrainStepInfo): last step state information
        """
        raise NotImplementedError

class DynamicLossScaler(LossScaler):
    r"""Default implementation for :py:class:`.LossScaler` class used for mixed precision

    This loss scaler works by assuming an initial scale, which is doubled every time a certain number of
    (stable) training steps are performed without exploding gradients (overflow or reach infinity).
    When at least one of the gradients explode, loss scale is divided by 2.

    Users can use this class in two ways:

        1. Enable mixed precision and not setting a loss scaler class. Default values are used
        2. Enable mixed precision and instantiate this class to override default arguments

    Static loss scaling can be achieved by setting :py:attr:`.automatic_update` to :py:obj:`False`
    and not performing manual :py:meth:`update` in train loop.

    Args:
        automatic_update (bool, default is False): boolean switch that allows :py:meth:`ORTTrainer.train_step`
            to automatically perform loss scaling. If False, an explicit call to :py:meth:`.update` must be done by the user,
            otherwise static loss scaling is performed.
        loss_scale (default is 1 << 16): A float that represents current loss scale
        up_scale_window (int, default is 2000): number of stable train steps before doubling loss scale
        min_loss_scale (float, default is 1): min value for the loss scale. Used when loss scale is decreased
        max_loss_scale (float, default is 1 << 24): max value for the loss scale. Used when loss scale is increased

    Example with default values:
        .. code-block:: python

            scaler1 = amp.DynamicLossScaler()
            print(f'Default loss scale is {scaler1.loss_scale}')

    Example with user specified values:
        .. code-block:: python

            scaler2 = amp.DynamicLossScaler(loss_scale=1<<8)
            print(f'Custom loss scale is {scaler2.loss_scale}')
    """
    def __init__(self, automatic_update=True,
                 loss_scale=float(1 << 16),
                 up_scale_window=2000,
                 min_loss_scale=1.0,
                 max_loss_scale=float(1 << 24)):
        super().__init__()
        self.automatic_update = automatic_update
        self.loss_scale = loss_scale
        self.up_scale_window = up_scale_window
        self.min_loss_scale = min_loss_scale
        self.max_loss_scale = max_loss_scale

        self._initial_loss_scale = loss_scale
        self._stable_steps_count = 0

    def reset(self):
        self.loss_scale = self._initial_loss_scale
        self._stable_steps_count = 0

    def update(self, train_step_info):
        if train_step_info.all_finite:
            self._stable_steps_count += 1

            if self._stable_steps_count >= self.up_scale_window:
                self.loss_scale = min(self.max_loss_scale, self.loss_scale * 2)
                self._stable_steps_count = 0
        else:
            self.loss_scale = max(self.min_loss_scale, self.loss_scale / 2)
            self._stable_steps_count = 0

