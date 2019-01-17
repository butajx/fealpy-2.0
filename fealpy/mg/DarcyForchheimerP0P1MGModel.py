import numpy as np
from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack, bmat, spdiags
from numpy.linalg import norm
from scipy.sparse.linalg import cg, inv, spsolve
from ..functionspace.lagrange_fem_space import LagrangeFiniteElementSpace
from ..functionspace.lagrange_fem_space import VectorLagrangeFiniteElementSpace
from ..mesh import TriangleMesh

class DarcyForchheimerP0P1MGModel:

    def __init__(self, pde, mesh, n):
        self.pde = pde
        self.uspaces = []
        self.pspaces = []
        self.IMatrix = []

        mesh0 = TriangleMesh(mesh.node, mesh.ds.cell)
        uspace = VectorLagrangeFiniteElementSpace(mesh0, p=0, spacetype='D')
        self.uspaces.append(uspace)
        pspace = LagrangeFiniteElementSpace(mesh0, p=1, spacetype='C')
        self.pspaces.append(pspace)

        for i in range(n):
            I0, I1 = mesh.uniform_refine(returnim=True)
            self.IMatrix.append((I0[0], I1[0]))
            mesh0 = TriangleMesh(mesh.node, mesh.ds.cell)
            uspace = VectorLagrangeFiniteElementSpace(mesh0, p=0, spacetype='D')
            self.uspaces.append(uspace)
            pspace = LagrangeFiniteElementSpace(mesh0, p=1, spacetype='C')
            self.pspaces.append(pspace)

        self.uh = self.uspaces[-1].function()
        self.ph = self.pspaces[-1].function()

        self.uI = self.uspaces[-1].interpolation(pde.velocity)
        self.pI = self.pspaces[-1].interpolation(pde.pressure)

        self.nlevel = n + 1
        
    def stiff_matrix(self):
        A = pspaces[-1].stiff_matrix()
    

    def compute_initial_value(self):
        mesh = self.pspaces[-1].mesh
        pde = self.pde
        mu = pde.mu
        rho = pde.rho

        bc = np.array([1/3,1/3,1/3], dtype=mesh.ftype)##weight
        gphi = self.pspaces[-1].grad_basis(bc)
        cellmeasure = mesh.entity_measure('cell')

        NC = mesh.number_of_cells()
        NN = mesh.number_of_nodes()
        scaledArea = mu/rho*cellmeasure

        A11 = spdiags(np.repeat(scaledArea, 2), 0, 2*NC, 2*NC)

        phi = self.uspaces[-1].basis(bc)
        A21 = np.einsum('ijm, km, i->ijk', gphi, phi, cellmeasure)

        cell2dof0 = self.uspaces[-1].cell_to_dof()
        ldof0 = self.uspaces[-1].number_of_local_dofs()
        cell2dof1 = self.pspaces[-1].cell_to_dof()
        ldof1 = self.pspaces[-1].number_of_local_dofs()
		
        gdof0 = self.uspaces.number_of_global_dofs()
        gdof1 = self.pspaces.number_of_global_dofs()
        I = np.einsum('ij, k->ijk', cell2dof1, np.ones(ldof0))
        J = np.einsum('ij, k->ikj', cell2dof0, np.ones(ldof1))

        A21 = csr_matrix((A21.flat, (I.flat, J.flat)), shape=(gdof1, gdof0))
        A12 = A21.transpose()

        A = bmat([(A11, A12), (A21, None)], format='csr', dtype=np.float)

        cc = mesh.entity_barycenter('cell')## the center of cell
        ft = pde.f(cc)*np.c_[cellmeasure, cellmeasure]
        f = ft.flatten()
		
        cell2edge = mesh.ds.cell_to_edge()
        ec = mesh.entity_barycenter('edge')
        mid1 = ec[cell2edge[:,1], :]
        mid2 = ec[cell2edge[:,2], :]
        mid3 = ec[cell2edge[:,0], :]
        
        bt1 = cellmeasure*(pde.g(mid2) + pde.g(mid3))/6
        bt2 = cellmeasure*(pde.g(mid3) + pde.g(mid1))/6
        bt3 = cellmeasure*(pde.g(mid1) + pde.g(mid2))/6

        b = np.bincount(np.ravel(cell, 'F'), weight=np.r_[bt1,bt2,bt3], minlenth = NN)
		
		## Neumann boundary condition
        isBDEdge = mesh.ds.boundary_edge_flag()
        edge2node = mesh.ds.edge_to_node()
        bdEdge = edge[isBDEdge, :]
        d = np.sqrt(np.sum((node[edge2node[isBDEdge, 0], :]\
            - node[edge2node[isBDEdge, 1], :]**2, 1)))
        mid = ec[isBDEdge, :]

        ii = np.c_[d*pde.Neumann_boundary(mid)/2, d*pde.Neumann_boundary(mid)/2]
        g = np.bincount(np.ravel(bdEdge), weights = ii.flatten(), minlength=NN)
		
        g = g - b[2*NC:]

        ## Solver
        b1 = np.r_[b[:2*NC], g]
        up = np.zeros(2*NC+NN, dtype=np.float)
        idx = np.arange(2*NC+NN-1)
        up[idx] = spsolve(A[idx, :][:, idx], b1[idx])
        u = up[:2*NC]
        p = up[2*NC:]
        c = np.sum(np.mean(p,1)*cellmeasure)/np.sum(cellmeasure)
        return u,p

