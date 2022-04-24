import copy
import datetime
import time
import sys
import torch
import models
from collections import OrderedDict
from config import cfg
from utils import to_device, collate, make_optimizer, make_scheduler


class SparsityIndex:
    def __init__(self, q):
        self.q = q
        self.si = []

    def make_sparsity_index(self, model, mask=None):
        si = []
        for i in range(len(self.q)):
            si_i = OrderedDict()
            for name, param in model.state_dict().items():
                parameter_type = name.split('.')[-1]
                if 'weight' in parameter_type:
                    if mask is not None:
                        param = param * mask[name].to(param.device).float()
                    si_i[name] = torch.linalg.norm(param, 1, dim=-1) / torch.linalg.norm(param, self.q[i], dim=-1)
            si.append(si_i)
        self.si.append(si)
        return


class Compression:
    def __init__(self, prune_ratio, prume_mode):
        self.init_model_state_dict = models.load_init_state_dict(cfg['seed'])
        self.mask = [self.make_mask(self.init_model_state_dict)]
        self.prune_ratio = prune_ratio
        self.prume_mode = prume_mode

    def make_mask(self, model_state_dict):
        mask = OrderedDict()
        for name, param in model_state_dict.items():
            parameter_type = name.split('.')[-1]
            if 'weight' in parameter_type:
                mask[name] = param.new_ones(param.size(), dtype=torch.bool)
        return mask

    def prune(self, model):
        if self.prune_mode[-1] == 'global':
            new_mask = OrderedDict()
            for name, param in model.named_parameters():
                parameter_type = name.split('.')[-1]
                if 'weight' in parameter_type:
                    mask = self.mask[-1][name]
                    masked_param = param[mask]
                    pivot_param = masked_param.abs()
                    percentile_value = torch.quantile(pivot_param, self.prune_ratio)
                    percentile_mask = (param.data.abs() < percentile_value).to('cpu')
                    new_mask[name] = torch.where(percentile_mask, False, mask)
                    param.data = torch.where(new_mask[name].to(param.device), param.data,
                                             torch.tensor(0, dtype=torch.float, device=param.device))
        elif self.prune_mode[-1] == 'layer':
            new_mask = OrderedDict()
            for name, param in model.named_parameters():
                parameter_type = name.split('.')[-1]
                if 'weight' in parameter_type:
                    mask = self.mask[-1][name]
                    masked_param = param[mask]
                    pivot_param = masked_param.abs()
                    percentile_value = torch.quantile(pivot_param, self.prune_ratio)
                    percentile_mask = (param.data.abs() < percentile_value).to('cpu')
                    new_mask[name] = torch.where(percentile_mask, False, mask)
                    param.data = torch.where(new_mask[name].to(param.device), param.data,
                                             torch.tensor(0, dtype=torch.float, device=param.device))
        else:
            raise ValueError('Not valid prune mode')
        self.mask.append(new_mask)
        return

    def init(self, model):
        for name, param in model.named_parameters():
            parameter_type = name.split('.')[-1]
            if 'weight' in parameter_type:
                mask = self.mask[-1][name]
                param.data = torch.where(mask, self.init_model_state_dict[name],
                                         torch.tensor(0, dtype=torch.float)).to(param.device)
            if "bias" in parameter_type:
                param.data = self.init_model_state_dict[name].to(param.device)
        return

    def freeze_grad(self, model):
        for name, param in model.named_parameters():
            parameter_type = name.split('.')[-1]
            if 'weight' in parameter_type:
                mask = self.mask[-1][name]
                param.grad.data = torch.where(mask.to(param.device), param.grad.data,
                                              torch.tensor(0, dtype=torch.float, device=param.device))
        return
