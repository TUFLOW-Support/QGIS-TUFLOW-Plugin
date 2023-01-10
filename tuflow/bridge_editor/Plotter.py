import matplotlib.pyplot as plt
import numpy as np


class Plotter:

    def __init__(self, *args, **kwargs):
        self.fig = None
        self.ax = None
        self.annotation = None
        self.snap_marker = None
        self.background = None
        self._creating_background = False

    def subplots(self, *args, **kwargs):
        self.fig, self.ax =  plt.subplots(*args, **kwargs)
        self.fig.canvas.mpl_connect("motion_notify_event", self._hover)
        self.fig.canvas.mpl_connect("draw_event", self._on_draw)
        return self.fig, self.ax

    def get_legend_handles_labels(self):
        artists, labels = [], []
        if isinstance(self.ax, list) or isinstance(self.ax, tuple):
            axs = self.ax[:]
        else:
            axs = [self.ax]
        for ax in axs:
            artists_, labels_ = ax.get_legend_handles_labels()
            artists.extend(artists_)
            labels.extend(labels_)
            if self._has_twin(ax):
                artists_, labels_ = self._has_twin(ax).get_legend_handles_labels()
                artists.extend(artists_)
                labels.extend(labels_)
        return artists, labels

    def _on_draw(self, event):
        self.background = None

    def _hover(self, event):
        in_axes = self._in_axes(event)
        if not in_axes and not self.annotation and not self.snap_marker:
            return

        vis = False
        ax = event.inaxes
        snap_util = SnapUtil(event, None, None)
        if in_axes:
            artists, labels = self.get_legend_handles_labels()
            snap_util = SnapUtil(event, artists, labels)
            snap_util.calculate_closest()
            if snap_util.found:
                vis = True
                ax = snap_util.axes()

        if (self.annotation is None or self.annotation.axes) != ax and ax is not None:
            self._create_new_annotation(ax)

        if (self.snap_marker is None or self.snap_marker.axes) != ax and ax is not None:
            self._create_new_snap_marker(ax)

        self._update_hover_over_labels(vis, snap_util.point_xy(), snap_util.text(), snap_util.color())

        self._blitted_draw(ax)

    def _update_hover_over_labels(self, vis, point_xy, text, color):
        self.annotation.set_visible(vis)
        self.snap_marker.set_visible(vis)
        if not vis:
            return

        self.annotation.xy = point_xy
        self.annotation.set_text(text)
        self.annotation.xyann = (10., 10.)
        self.annotation.get_bbox_patch().set_facecolor(color)
        self.annotation.get_bbox_patch().set_alpha(0.3)
        self._correct_for_bounds()

        self.snap_marker.set_offsets([point_xy])
        self.snap_marker.set_zorder(100)

    def _correct_for_bounds(self):
        ax = self.annotation.axes
        trans = ax.transData.transform
        self.annotation.draw(self.fig.canvas.renderer)
        xy = self.annotation.xy
        padw = self.annotation.get_bbox_patch()._bbox_transmuter.pad * self.annotation.get_bbox_patch().get_width() * 2
        padh = self.annotation.get_bbox_patch()._bbox_transmuter.pad * self.annotation.get_bbox_patch().get_height() * 2
        if trans(xy)[0] + self.annotation.get_bbox_patch().get_width() + padw + padw + 5 > ax.bbox.p1[0]:
            self.annotation.xyann = (-self.annotation.get_bbox_patch().get_width() - 7, self.annotation.xyann[1])
        if trans(xy)[1] + self.annotation.get_bbox_patch().get_height() + padh + 5 > ax.bbox.p1[1]:
            self.annotation.xyann = (self.annotation.xyann[0], -self.annotation.get_bbox_patch().get_height() - 7)

    def _in_axes(self, event):
        if event is None or event.inaxes is None:
            return False

        if isinstance(self.ax, list) or isinstance(self.ax, tuple):
            axs = self.ax[:]
        else:
            axs = [self.ax]

        for ax in axs:
            if ax == event.inaxes:
                return True
            ax2 = self._has_twin(ax)
            if ax2 is not None and ax2 == event.inaxes:
                return True

        return False

    def _has_twin(self, ax):
        for other_ax in ax.figure.axes:
            if other_ax is ax:
                continue
            if other_ax.bbox.bounds == ax.bbox.bounds:
                return other_ax

    def _blitted_draw(self, ax):
        if ax is None:
            return

        if self.background is None:
            self._create_new_background(ax)

        self.fig.canvas.restore_region(self.background)
        ax.draw_artist(self.annotation)
        ax.draw_artist(self.snap_marker)
        self.fig.canvas.blit(ax.bbox)

    def _create_new_background(self, ax):
        if self._creating_background:
            return

        self._creating_background = True
        self.annotation.set_visible(False)
        self.annotation.set_visible(False)
        self.fig.canvas.draw()
        self.background = self.fig.canvas.copy_from_bbox(ax.bbox)
        self._creating_background = False
        self.annotation.set_visible(True)
        self.annotation.set_visible(True)

    def _create_new_annotation(self, ax):
        if self.annotation is not None:
            try:
                self.annotation.remove()
            except ValueError:
                pass
        self.annotation = ax.annotate("debug", xy=(15,15), xycoords='data',  textcoords="offset pixels",
                                      bbox=dict(boxstyle="round", fc="w"), xytext=(10., 10.))
        self.annotation.set_visible(False)

    def _create_new_snap_marker(self, ax):
        if self.snap_marker is not None:
            try:
                self.snap_marker.remove()
            except ValueError:
                pass
        self.snap_marker = ax.scatter(0, 0, 20, 'red')
        self.snap_marker.set_visible(False)


class SnapUtil:

    def __init__(self, event, artists, labels):
        self.event = event
        self.artists = artists
        self.labels = labels
        self.snapper = None
        self.found = False

    def calculate_closest(self):
        self.snapper = None
        for artist, label in zip(self.artists, self.labels):
            try:
                snapper = Snapper(self.event, artist, label)
                snapper.calculate_closest()
                if snapper.dist <= 3:
                    self.found = True
                    self.snapper = snapper
                    return
            except NotImplementedError:
                pass

    def point_xy(self):
        if self.snapper:
            return self.snapper.point_xy

    def axes(self):
        if self.snapper:
            return self.snapper.ax

    def text(self):
        if self.snapper:
            return self.snapper.annot

    def color(self):
        if self.snapper:
            return self.snapper.color


class Snapper:

    __slots__ = {'event', 'artist', 'labels', 'ax', 'point_xy', 'dist', 'annot', 'color'}

    def __new__(cls, *args):
        artist = args[1]
        if isinstance(artist, plt.Line2D):
            cls = Line2DSnapper
        elif isinstance(artist, plt.Polygon):
            cls = PolygonSnapper
        else:
            raise NotImplementedError

        return cls._init(*args)

    @classmethod
    def _init(cls, *args):
        self = object.__new__(cls)
        self.event, self.artist, self.labels = args
        self.point_xy = None
        self.dist = 9e29
        self.ax = self.artist.axes
        self.annot = None
        self.color = None
        return self

    def calculate_closest(self, data_=None):
        ax = self.event.inaxes
        trans = ax.transData.transform
        a = trans([self.event.xdata, self.event.ydata])

        ax = self.artist.axes
        trans = ax.transData.transform
        d = np.array([trans(x) for x in data_])

        mask = (d[:, 0] > (a[0] - a[0] * 0.1)) & (d[:, 0] < (a[0] + a[0] * 0.1))
        mask_start = np.where(mask == True)[0]

        if mask_start.shape[0]:
            mask_start = mask_start[0]
        else:
            return

        d = d[mask]

        close_points = np.array(
            [(np.absolute(np.array(x) - np.array(a)).sum(), i + mask_start) for i, x in enumerate(d) if
             np.isclose(x, a, atol=5).all()])
        if not close_points.any():
            return

        try:
            i = np.where(close_points[:, 0] == np.amin(close_points[:, 0]))[0][0]
        except:
            return

        self.point_xy = data_[int(close_points[:, 1][i])]
        self.dist = ((trans(self.point_xy)[0] - a[0]) ** 2 + (trans(self.point_xy)[1] - a[1]) ** 2) ** 0.5


class Line2DSnapper(Snapper):

    def calculate_closest(self, *args):
        Snapper.calculate_closest(self, list(zip(*self.artist.get_data())))
        if self.point_xy:
            self.annot = '{0:.3f}, {1:.3f}'.format(*self.point_xy)
            self.color = self.artist.get_color()


class PolygonSnapper(Snapper):

    def calculate_closest(self, *args):
        pass
