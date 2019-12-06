import numpy as np
import scipy.sparse as spsp
import networkx as nx

def get_node_in_neighbor(nid, csc_adj):
  """
  """
  return csc_adj.indices[csc_adj.indptr[nid]: csc_adj.indptr[nid+1]]


def get_in_neighbors(coo_adj, node_ids):
  """
  """
  csc_adj = coo_adj.tocsc()
  neighbors = []
  for nid in node_ids:
    neighbors.append(get_node_in_neighbor(nid, csc_adj))
  neighbors = np.unique(np.concatenate(tuple(neighbors)))
  return neighbors


def get_num_hop_in_neighbors(coo_adj, node_ids, num_hop, excluded_nodes=None):
  """
  Get num-hop neighbor idx for the given graph `coo_adj` and `node_ids`
  Return:
    nodes: list of nd arrays, [1-hop neighbors, 2-hop neighbors, ...]
  """
  select_mask = np.vectorize(exclude, excluded=['node_range'])

  neighbors = []
  for _ in range(num_hop):
    neighbors.append(get_in_neighbors(coo_adj, node_ids))
    if excluded_nodes is not None:
      mask = select_mask(nid=neighbors[-1], node_range=excluded_nodes)
      neighbors[-1] = neighbors[-1][mask]
  return neighbors


def get_sub_train_nids(sub2fullid, train_nids):
  """
  Get train nids under sub grpah namespace
  Params:
    sub_adj: coo sparse matrix for sub graph
    sub2fullid: np array mapping sub_adj node idx to full graph node idx
    train_nids: np array for training node idx under full grpah namespace
  ReturnL
    sub_train_nids: np array for training node idx under sub grpah namespace
  """
  isin_mask_vfunc = np.vectorize(include, excluded=['node_range'])
  sub_train_nids_mask = isin_mask_vfunc(nid=sub2fullid, node_range=train_nids)
  sub_train_nids = np.arange(len(sub2fullid))[sub_train_nids_mask]
  return sub_train_nids


def full2sub_nid(sub2fullid, full_nids):
  """
  Return an nd array with length of max(su2fullid) + 1.
  """
  full2subid = np.zeros(np.max(sub2fullid) + 1, dtype=np.int64)
  full2subid[sub2fullid] = np.arange(len(sub2fullid))
  return full2subid[full_nids]

def exclude(nid, node_range):
  return not nid in node_range

def include(nid, node_range):
  return nid in node_range


def draw_graph(sub_adj, sub2fullid=None):
  g = nx.from_scipy_sparse_matrix(sub_adj, create_using=nx.DiGraph())
  pos = nx.kamada_kawai_layout(g)
  #pos = nx.spring_layout(g)
  if sub2fullid is None:
    nx.draw(g, pos, with_labels=True, arrows=True, node_color=[[.7, .7, .7]])
  else:
    labels = {idx: sub2fullid[idx] for idx in range(len(sub2fullid))}
    nx.draw(g, pos, arrows=True, node_color=[[.7, .7, .7]])
    _ = nx.draw_networkx_labels(g, pos, labels=labels)