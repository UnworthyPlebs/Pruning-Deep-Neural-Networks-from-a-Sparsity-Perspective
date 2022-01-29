import torch
import torch.nn.functional as F
from config import cfg
from utils import recur


def Accuracy(output, target, topk=1):
    with torch.no_grad():
        if target.dtype != torch.int64:
            target = (target.topk(1, 1, True, True)[1]).view(-1)
        batch_size = target.size(0)
        pred_k = output.topk(topk, 1, True, True)[1]
        correct_k = pred_k.eq(target.view(-1, 1).expand_as(pred_k)).float().sum()
        acc = (correct_k * (100.0 / batch_size)).item()
    return acc


def InceptionScore(target, splits=1):
    with torch.no_grad():
        N = target.size(0)
        pred = F.softmax(target, dim=-1)
        split_scores = []
        for k in range(splits):
            part = pred[k * (N // splits): (k + 1) * (N // splits), :]
            py = torch.mean(part, dim=0)
            scores = F.kl_div(py.log().view(1, -1).expand_as(part), part, reduction='batchmean').exp()
            split_scores.append(scores)
        inception_score = torch.mean(torch.tensor(split_scores)).item()
    return inception_score


class Metric(object):
    def __init__(self, data_name, metric_name):
        self.data_name = data_name
        self.metric_name = metric_name
        self.pivot, self.pivot_name, self.pivot_direction = self.make_pivot(data_name)
        self.metric = {'Loss': (lambda input, output: output['loss'].item()),
                       'Accuracy': (lambda input, output: recur(Accuracy, output['target'], input['target'])),
                       'InceptionScore': (lambda input, output: recur(InceptionScore, output['target']))}

    def make_pivot(self, data_name):
        if data_name in ['MNIST', 'SVHN', 'CIFAR10', 'CIFAR100']:
            pivot = -float('inf')
            pivot_direction = 'up'
            pivot_name = 'Accuracy'
        else:
            raise ValueError('Not valid data name')
        return pivot, pivot_name, pivot_direction

    def evaluate(self, metric_names, input, output):
        evaluation = {}
        for metric_name in metric_names:
            evaluation[metric_name] = self.metric[metric_name](input, output)
        return evaluation

    def compare(self, val):
        if self.pivot_direction == 'down':
            compared = self.pivot > val
        elif self.pivot_direction == 'up':
            compared = self.pivot < val
        else:
            raise ValueError('Not valid pivot direction')
        return compared

    def update(self, val):
        self.pivot = val
        return
