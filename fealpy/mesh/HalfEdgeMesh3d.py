import numpy as np
from .adaptive_tools import mark


class HalfEdgeMesh3d():
    def __init__(self, node, halfedge, subdomain, NE=None, NF=None):
        """
        Parameters
        ----------
            halfedge:
                halfedge[i, 0] : index of the node pointed by i-th halfedge
                halfedge[i, 1] : index of the face enclosed by i-th halfedge
                halfedge[i, 2] : index of the cell enclosed by of i-th halfedge
                halfedge[i, 3] : index of the next halfedge of i-th halfedge
                halfedge[i, 4] : index of the prev halfedge of i-th halfedge

                halfedge[i, 5] : index of the opposite halfedge of i-th halfedge, 
                    and the halfedge[i, 6]-th and i-th halfedge in the neighbor
                    cell which chare face halfedge[i, 1] with cell halfedge[i,
                    2].
                halfedge[i, 6] : index of the opposite halfedge of i-th halfedge, 
                    and the halfedge[i, 5]-th and i-th halfedge are in the same cell.
            subdomain: (NC, )the sub domain flag of each cell blong to
        """
        self.itype = halfedge.dtype
        self.ftype = node.dtype

        self.node = node
        NN = node.shape[0]
        self.ds = HalfEdgeMesh3dDataStructure(halfedge, subdomain, NN=NN, NE=NE, NF=NF)
        self.meshtype = 'halfedge3d'

        self.halfedgedata = {}
        self.celldata = {}
        self.nodedata = {}
        self.edgedata = {}
        self.facedata = self.edgedata
        self.meshdata = {}

        # 网格节点的自由度标记数组
        # 0: 固定点
        # 1: 边界上的点
        # 2: 区域内部的点
        self.nodedata['dof'] = nodedof

        self.init_level_info()

    @classmethod
    def from_mesh(self, mesh):
        NN = mesh.number_of_nodes()
        NE = mesh.number_of_edges()
        NF = mesh.number_of_faces()
        NC = mesh.number_of_cells()

        node = mesh.entity('node')
        edge = mesh.entity('edge')
        face = mesh.entity('face')
        cell = mesh.entity('cell')

        FE = mesh.ds.FE # number of edges of each face
        NHE = 2*NF*FE
        halfedge = np.zeros((NHE, 7), dtype=mesh.itype)

        idx0 = np.arange(FE)
        idx1 = np.zeros(FE, dtype=np.int)
        idx1[0] = idx0[-1]
        idx1[1:] = idx0[0:-1]
        halfedge[0::2, 0] = face[:, idx0].flat
        halfedge[1::2, 0] = face[:, idx1].flat

        halfedge[0::2, 1] = np.repeat(range(NF), FE)
        halfedge[1::2, 1] = halfedge[0::2, 1]

        face2cell = mesh.ds.face_to_cell()
        isBdFace = mesh.ds.boundary_face_flag()
        lCell = face2cell[:, 0] + 1
        rCell = face2cell[:, 1]
        rCell[isBdFace] = 0
        rCell[~isBdFace] += 1
        halfedge[0::2, 2] = np.repeat(lCell, FE) 
        halfedge[1::2, 2] = np.repeat(rCell, FE) 

        # dual halfedge in the opposite cell
        halfedge[0::2, 5] = range(1, NHE, 2)
        halfedge[1::2, 5] = range(0, NHE, 2) 
        
        hidx0 = halfedge[0::2, 5].reshape(-1, FE)
        hidx1 = halfedge[1::2, 5].reshape(-1, FE)
        
        nex = np.r_[range(1, FE), 0]
        # next
        halfedge[0::2, 3] = hidx0[:, nex].flat 
        halfedge[1::2, 3] = hidx1[:, nex].flat 
        # prev
        halfedge[halfedge[:, 3], 4] = range(NHE) 

        # dual halfedge in the same cell
        edge = np.zeros((NHE, 3), dtype=facets.dtype)
        edge[:, 0] = halfedge[:, 0]
        edge[:, 1] = halfedge[halfedge[:, 4], 0]
        edge[:, 2] = halfedge[:, 2] # cell blong to

        flag = (edge[:, 0] > edge[:, 1])
        idx = edge[flag, 0]
        edge[flag, 0] = edge[flag, 1]
        edge[flag, 1] = idx
        idx = np.lexsort((edge[:, 0], edge[:, 1], edge[:, 2)).reshape(-1, 2)
        halfedge[idx[:, 0], 6] = idx[:, 1]
        halfedge[idx[:, 1], 6] = idx[:, 0] 

        subdomain = np.zeros(NC+1, dtype=mesh.itype)
        if 'subdomain' in mesh.celldata:
            subdomain[1:] = mesh.celldata['subdomain'] 
        else:

        return cls(node, halfedge, subdomain, NE=NE, NF=NF) 




class HalfEdgeMesh3dDataStructure():
    def __init__(self, NN, halfedge, subdomain, NN=None, NE=None, NF=None):
        self.reinit(NN, halfedge, subdomain, NN=NN, NE=NE, NF=NF)

    def reinit(self, halfedge, subdomain, NN=None, NE=None, NF=None):
        if NN is None:
            self.NN = max(halfedge[:, 0])
        else:
            self.NN = NN

        self.NE = NE
        self.NC = NC
        self.NF = NF 
        self.halfedge = halfedge
        self.itype = halfedge.dtype

        self.hcell = np.zeros(NC, dtype=self.itype) # hcell[i] is the index of one face of i-th cell
        self.hface = np.zeros(NF, dtype=self.itype) # hface[i] is the index of one halfedge of i-th face 
        self.hedge = hedge # hedge[i] is the index of one halfedge of i-th edge
