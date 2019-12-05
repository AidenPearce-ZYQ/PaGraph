import os
import sys
# set environment
module_name ='PaGraph'
modpath = os.path.abspath('.')
if module_name in modpath:
  idx = modpath.find(module_name)
  modpath = modpath[:idx]
sys.path.append(modpath)

import argparse, time
import torch
import torch.nn as nn
import torch.distributed as dist
import torch.multiprocessing as mp
import torch.nn.functional as F
import numpy as np
import dgl
import PaGraph.data as data

def gnneval(args, infer_model, train_model, graph, labels, rank, test_nid):
  """
  Evaluation just on a single machine
  """
  ctx = torch.device(rank)
  for infer_param, param in zip(infer_model.parameters(), train_model.parameters()):    
    infer_param.data.copy_(param.data)
  infer_model.cuda(ctx)

  num_acc = 0.
  step = 0
  for nf in dgl.contrib.sampling.NeighborSampler(graph,args.batch_size,
                                                 graph.number_of_nodes(),
                                                 neighbor_type='in',
                                                 num_workers=16,
                                                 num_hops=args.n_layers+1,
                                                 seed_nodes=test_nid):
    nf.copy_from_parent(ctx=ctx)
    infer_model.eval()
    with torch.no_grad():
      pred = infer_model(nf)
      batch_nids = nf.layer_parent_nid(-1)
      batch_labels = labels[batch_nids].cuda(rank)
      num_acc += (pred.argmax(dim=1) == batch_labels).sum().cpu().item()
    step += 1
    if step % 20 == 0:
      print('test step [{}]'.format(step))
    
  print("Test Accuracy {:.4f}".format(num_acc / len(test_nid)))


def main(args):

  dataname = os.path.basename(args.dataset)
  g = dgl.contrib.graph_store.create_graph_from_store(dataname, "shared_mem")
  labels = data.get_labels(args.dataset)
  n_classes = len(np.unique(labels))
  train_mask, val_mask, test_mask = data.get_masks(args.dataset)
  test_nid = np.nonzero(test_mask)[0].astype(np.int64)

  labels = torch.LongTensor(labels)

  if args.arch == 'gcn-nssc':
    from PaGraph.model.pytorch.gcn_nssc import GCNSampling, GCNInfer
    train_model = torch.load(
      os.path.join(args.ckpt, args.arch + '_' + str(args.epoch))
    )
    infer_model = GCNInfer(args.feat_size,
                           args.n_hidden,
                           n_classes,
                           args.n_layers,
                           F.relu)
  else:
    print('Unknown arch')
    sys.exit(-1)
  
  gnneval(args, infer_model, train_model, g, labels, 0, test_nid)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='GCNInfer')

  parser.add_argument("--gpu", type=int, default=None,
                      help="gpu id. such as 0 or 1 or 2")
  parser.add_argument("--dataset", type=str, default=None,
                      help="path to the dataset folder")
  parser.add_argument("--arch", type=str, default='gcn-nssc',
                      help='model arch')
  # model arch
  parser.add_argument("--feat-size", type=int, default=300,
                      help='input feature size')
  parser.add_argument("--n-hidden", type=int, default=128,
                      help="number of hidden gcn units")
  parser.add_argument("--n-layers", type=int, default=1,
                      help="number of hidden gcn layers")
  # training hyper-params
  parser.add_argument("--epoch", type=int, default=60,
                      help="eval epcoh")
  parser.add_argument("--batch-size", type=int, default=512,
                      help="batch size")
  
  parser.add_argument("--ckpt", type=str, default='checkpoint',
                      help="checkpoint dir")
  
  args = parser.parse_args()

  os.environ['CUDA_VISIBLE_DEVICES'] = str(args.gpu)
  
  main(args)