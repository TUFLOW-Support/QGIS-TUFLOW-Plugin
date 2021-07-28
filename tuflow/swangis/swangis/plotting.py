import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

mpl.interactive(True)

def plotGrid(grid, z=None, image=None, **kwargs):
    nodes = grid.getNodes()
    faces = grid.getFaces()

    xy = np.dstack((nodes[faces, 0], nodes[faces, 1]))

    if z is None:
        patch = PolyCollection(verts=xy, **kwargs)
    else:
        patch = PolyCollection(verts=xy, array=z)

    f = plt.figure()
    ax = f.add_axes([0.1, 0.1, 0.8, 0.8])

    ax.add_collection(patch)

    ax.set_xlim(nodes[:, 0].min(), nodes[:, 0].max())
    ax.set_ylim(nodes[:, 1].min(), nodes[:, 1].max())

    ax.set_aspect('equal')

    return f, ax