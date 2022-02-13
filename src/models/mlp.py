import torch
import torch.nn as nn
import math
from config import cfg
from .utils import init_param_classifier, loss_fn


class MLP(nn.Module):
    def __init__(self, data_shape, hidden_size, scale_factor, num_layers, activation, target_size):
        super().__init__()
        input_size = math.prod(data_shape)
        blocks = []
        for _ in range(num_layers):
            blocks.append(nn.Linear(input_size, hidden_size))
            if activation == 'relu':
                blocks.append(nn.ReLU())
            elif activation == 'sigmoid':
                blocks.append(nn.Sigmoid())
            else:
                raise ValueError('Not valid activation')
            input_size = hidden_size
            hidden_size = hidden_size * scale_factor
        blocks.append(nn.Linear(input_size, target_size))
        self.blocks = nn.Sequential(*blocks)

    def f(self, x):
        x = self.blocks(x)
        return x

    def forward(self, input):
        output = {}
        x = self.f(input['data'])
        output['target'] = x
        if 'target' in input:
            output['loss'] = loss_fn(output['target'], input['target'])
        return output


def mlp():
    data_shape = cfg['data_shape']
    target_size = cfg['target_size']
    hidden_size = cfg['mlp']['hidden_size']
    scale_factor = cfg['mlp']['scale_factor']
    num_layers = cfg['mlp']['num_layers']
    activation = cfg['mlp']['activation']
    model = Conv(data_shape, hidden_size, scale_factor, num_layers, activation, target_size)
    model.apply(init_param_classifier)
    return model
