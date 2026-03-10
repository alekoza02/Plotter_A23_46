from copy import deepcopy
from time import perf_counter_ns

import numpy as np
import numpy.typing as npt

DRAW_DEBUG = False

class Canvas:
    def __init__(self):
        self.aspect_ratio: float
        self.width: int
        self.height: int

        self.plots_grid: Grid = Grid()

        self.output_path: str

    def __set_aspect_ratio(self, aspect_ratio: float = 1):
        self.aspect_ratio = aspect_ratio

    def set_image_size(self, width, height):
        self.width = width
        self.height = height
        self.plots_grid.global_width = width
        self.plots_grid.global_height = height
        self.__set_aspect_ratio(self.width / self.height)

        self.plots_grid.set_grid_padding(min(self.width, self.height) / 100)

    def set_output_path(self, output_path="default_output.svg"):
        self.output_path = output_path

    def save_image(self):
        start_timer = perf_counter_ns()

        HEADER = f'''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg"
            width="{self.width}" height="{self.height}"
            viewBox="0 0 {self.width} {self.height}">
        '''
        FOOTER = "</svg>\n"

        for plot in self.plots_grid.plots.values():
            plot.draw_data()

        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(HEADER)
            for shape in self.plots_grid.batch:
                f.write("  " + shape + "\n")
            f.write(FOOTER)

        stop_timer = perf_counter_ns()
        print(f"Saving took: {(stop_timer - start_timer) / 1e6:.1f}ms")
        print(f"Which means this could update around {1 / ((stop_timer - start_timer) / 1e9):.1f} times a second")


class Grid:
    def __init__(self):
        self.grid_padding = 15
        self.IDs: set[str] = set()
        self.BBs: dict[str, list[int]] = {}
        self.plots: dict[str, Plot] = {}
        self.global_width: int
        self.global_height: int

    def set_grid_padding(self, grid_padding: float = 10):
        self.grid_padding = grid_padding

    def add_plot(self, id, BB):
        self.IDs.add(id)

        BB_padding = [BB[0] + self.grid_padding, BB[1] + self.grid_padding, BB[2] - 2 * self.grid_padding, BB[3] - 2 * self.grid_padding]

        self.BBs[id] = BB_padding
        self.plots[id] = Plot(id, BB_padding[0], BB_padding[1], BB_padding[2], BB_padding[3], self.global_width, self.global_height)

    @property
    def batch(self):
        ris = [shape for plot in self.plots.values() for shape in plot.batch.shapes]
        return ris


class Plot:
    def __init__(self, id, x, y, width, height, global_width, global_height):
        self.id = id

        self.ticks_padding = [7, 7]
        self.ticks_font_size = [16, 16]

        self.plot_padding = 15

        self.target_bins_ticks = [8, 8]

        self.global_sizes = [global_width, global_height]
        self.data_BB_xywh_normalized: list[float] = [0.2, 0.2, 0.75, 0.65]
        self.plot_BB_xywh_original = [x, y, width, height]

        self.labels: list[Label] = [
            Label(DynamicCoordinate("0px"), DynamicCoordinate("0px"), "X Label", 40, "cd", 0, 0, "#94b1ff"),
            Label(DynamicCoordinate("0px"), DynamicCoordinate("0px"), "Y Label", 40, "cu", 0, 0, "#94b1ff", rotate=-90),
            Label(DynamicCoordinate("0px"), DynamicCoordinate("0px"), "", 40, "cd", 0, 0, "#94b1ff", rotate=-90),
            Label(DynamicCoordinate("0px"), DynamicCoordinate("0px"), "Title", 40, "cu", 0, 0, "#94b1ff")
        ]

        self.update_coords_mapping()

        self.batch = SVG_batch()

        self.data_read_only: npt.NDArray[np.float64]

    def update_coords_mapping(self):

        self.plot_BB_xywh_padded = [self.plot_BB_xywh_original[0] + self.plot_padding, self.plot_BB_xywh_original[1] + self.plot_padding, self.plot_BB_xywh_original[2] - 2 * self.plot_padding, self.plot_BB_xywh_original[3] - 2 * self.plot_padding,]
        self.data_BB_xywh = [self.plot_BB_xywh_padded[2] * self.data_BB_xywh_normalized[0], self.plot_BB_xywh_padded[3] * self.data_BB_xywh_normalized[1], self.plot_BB_xywh_padded[2] * self.data_BB_xywh_normalized[2], self.plot_BB_xywh_padded[3] * self.data_BB_xywh_normalized[3]]

        self.data_BB_verts = [
            [self.plot_BB_xywh_padded[0] + self.data_BB_xywh[0], self.plot_BB_xywh_padded[1]+ self.plot_BB_xywh_padded[3] - (self.data_BB_xywh[1])],
            [self.plot_BB_xywh_padded[0] + self.data_BB_xywh[0], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3] - (self.data_BB_xywh[1] + self.data_BB_xywh[3])],
            [self.plot_BB_xywh_padded[0] + self.data_BB_xywh[0] + self.data_BB_xywh[2], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3] - (self.data_BB_xywh[1])],
            [self.plot_BB_xywh_padded[0] + self.data_BB_xywh[0] + self.data_BB_xywh[2], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3] - (self.data_BB_xywh[1] + self.data_BB_xywh[3])],
        ]

        # X label
        self.labels[0].pos[0].set_new_dynamic_coordinate(f"{self.data_BB_xywh_normalized[0] + self.data_BB_xywh_normalized[2]/2}%w")
        self.labels[0].pos[1].set_new_dynamic_coordinate(f"1%h")
        
        # Y label
        self.labels[1].pos[0].set_new_dynamic_coordinate("0px")
        self.labels[1].pos[1].set_new_dynamic_coordinate(f"{1 - self.data_BB_xywh_normalized[1] - self.data_BB_xywh_normalized[3]/2}%h")
        
        # 2Y label
        self.labels[2].pos[0].set_new_dynamic_coordinate("1%w")
        self.labels[2].pos[1].set_new_dynamic_coordinate(f"{1 - self.data_BB_xywh_normalized[1] - self.data_BB_xywh_normalized[3]/2}%h")
        
        # Title
        self.labels[3].pos[0].set_new_dynamic_coordinate(f"{self.data_BB_xywh_normalized[0] + self.data_BB_xywh_normalized[2]/2}%w")
        self.labels[3].pos[1].set_new_dynamic_coordinate(f"0px")

        [label.pos[0].set_coord_database(self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[3], self.global_sizes[0], self.global_sizes[1]) for label in self.labels]
        [label.pos[1].set_coord_database(self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[3], self.global_sizes[0], self.global_sizes[1]) for label in self.labels]
        [label.pos[0].parser() for label in self.labels]
        [label.pos[1].parser() for label in self.labels]

    def draw_debug_info(self):
        # Plot name
        self.batch.add_text(f"Plot ID: {self.id}", self.data_BB_verts[1][0] + self.data_BB_xywh[2] / 2, self.data_BB_verts[1][1] - 10, font_size=24, fill_color='#dc143c')

        # BB debug
        self.batch.add_line(self.plot_BB_xywh_original[0], self.plot_BB_xywh_original[1], self.plot_BB_xywh_original[0], self.plot_BB_xywh_original[1] + self.plot_BB_xywh_original[3], stroke_color='#dc143c', stroke_width=2)
        self.batch.add_line(self.plot_BB_xywh_original[0], self.plot_BB_xywh_original[1], self.plot_BB_xywh_original[0] + self.plot_BB_xywh_original[2], self.plot_BB_xywh_original[1], stroke_color='#dc143c', stroke_width=2)
        self.batch.add_line(self.plot_BB_xywh_original[0] + self.plot_BB_xywh_original[2], self.plot_BB_xywh_original[1] + self.plot_BB_xywh_original[3], self.plot_BB_xywh_original[0], self.plot_BB_xywh_original[1] + self.plot_BB_xywh_original[3], stroke_color='#dc143c', stroke_width=2)
        self.batch.add_line(self.plot_BB_xywh_original[0] + self.plot_BB_xywh_original[2], self.plot_BB_xywh_original[1] + self.plot_BB_xywh_original[3], self.plot_BB_xywh_original[0] + self.plot_BB_xywh_original[2], self.plot_BB_xywh_original[1], stroke_color='#dc143c', stroke_width=2)

        self.batch.add_circle(self.plot_BB_xywh_original[0], self.plot_BB_xywh_original[1], 5, fill_color='#dc143c')
        self.batch.add_circle(self.plot_BB_xywh_original[0], self.plot_BB_xywh_original[1] + self.plot_BB_xywh_original[3], 5, fill_color='#dc143c')
        self.batch.add_circle(self.plot_BB_xywh_original[0] + self.plot_BB_xywh_original[2], self.plot_BB_xywh_original[1], 5, fill_color='#dc143c')
        self.batch.add_circle(self.plot_BB_xywh_original[0] + self.plot_BB_xywh_original[2], self.plot_BB_xywh_original[1] + self.plot_BB_xywh_original[3], 5, fill_color='#dc143c')
        self.batch.add_text("Plot BB", self.plot_BB_xywh_original[0] + 5, self.plot_BB_xywh_original[1] + 5, font_size=16, fill_color='#dc143c', anchor='lu')

        # BB + padding debug
        self.batch.add_line(self.plot_BB_xywh_padded[0], self.plot_BB_xywh_padded[1], self.plot_BB_xywh_padded[0], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3], stroke_color="#e65f5f", stroke_width=2)
        self.batch.add_line(self.plot_BB_xywh_padded[0], self.plot_BB_xywh_padded[1], self.plot_BB_xywh_padded[0] + self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[1], stroke_color='#e65f5f', stroke_width=2)
        self.batch.add_line(self.plot_BB_xywh_padded[0] + self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3], self.plot_BB_xywh_padded[0], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3], stroke_color='#e65f5f', stroke_width=2)
        self.batch.add_line(self.plot_BB_xywh_padded[0] + self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3], self.plot_BB_xywh_padded[0] + self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[1], stroke_color='#e65f5f', stroke_width=2)

        self.batch.add_circle(self.plot_BB_xywh_padded[0], self.plot_BB_xywh_padded[1], 5, fill_color='#e65f5f')
        self.batch.add_circle(self.plot_BB_xywh_padded[0], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3], 5, fill_color='#e65f5f')
        self.batch.add_circle(self.plot_BB_xywh_padded[0] + self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[1], 5, fill_color='#e65f5f')
        self.batch.add_circle(self.plot_BB_xywh_padded[0] + self.plot_BB_xywh_padded[2], self.plot_BB_xywh_padded[1] + self.plot_BB_xywh_padded[3], 5, fill_color='#e65f5f')

        self.batch.add_text("Plot BB + padding", self.plot_BB_xywh_padded[0] + 5, self.plot_BB_xywh_padded[1] + 5, font_size=16, fill_color='#e65f5f', anchor='lu')

        # Data BB
        self.batch.add_line(self.data_BB_verts[0][0], self.data_BB_verts[0][1], self.data_BB_verts[1][0], self.data_BB_verts[1][1], stroke_color='#ffaaaa', stroke_width=2)
        self.batch.add_line(self.data_BB_verts[0][0], self.data_BB_verts[0][1], self.data_BB_verts[2][0], self.data_BB_verts[2][1], stroke_color='#ffaaaa', stroke_width=2)
        self.batch.add_line(self.data_BB_verts[3][0], self.data_BB_verts[3][1], self.data_BB_verts[1][0], self.data_BB_verts[1][1], stroke_color='#ffaaaa', stroke_width=2)
        self.batch.add_line(self.data_BB_verts[3][0], self.data_BB_verts[3][1], self.data_BB_verts[2][0], self.data_BB_verts[2][1], stroke_color='#ffaaaa', stroke_width=2)

        self.batch.add_circle(self.data_BB_verts[0][0], self.data_BB_verts[0][1], 5, fill_color='#ffaaaa')
        self.batch.add_circle(self.data_BB_verts[1][0], self.data_BB_verts[1][1], 5, fill_color='#ffaaaa')
        self.batch.add_circle(self.data_BB_verts[2][0], self.data_BB_verts[2][1], 5, fill_color='#ffaaaa')
        self.batch.add_circle(self.data_BB_verts[3][0], self.data_BB_verts[3][1], 5, fill_color='#ffaaaa')

        self.batch.add_text("Data BB", self.data_BB_verts[1][0] + 5, self.data_BB_verts[1][1] + 5, font_size=16, fill_color='#ffaaaa', anchor='lu')

        # Data BB
        self.batch.add_line(self.data_BB_verts[0][0],self.data_BB_verts[0][1],self.data_BB_verts[1][0],self.data_BB_verts[1][1],stroke_color="#ffaaaa",stroke_width=2,)
        self.batch.add_line(self.data_BB_verts[0][0],self.data_BB_verts[0][1],self.data_BB_verts[2][0],self.data_BB_verts[2][1],stroke_color="#ffaaaa",stroke_width=2,)
        self.batch.add_line(self.data_BB_verts[3][0],self.data_BB_verts[3][1],self.data_BB_verts[1][0],self.data_BB_verts[1][1],stroke_color="#ffaaaa",stroke_width=2,)
        self.batch.add_line(self.data_BB_verts[3][0],self.data_BB_verts[3][1],self.data_BB_verts[2][0],self.data_BB_verts[2][1],stroke_color="#ffaaaa",stroke_width=2,)

        self.batch.add_circle(self.data_BB_verts[0][0], self.data_BB_verts[0][1], 5, fill_color="#ffaaaa")
        self.batch.add_circle(self.data_BB_verts[1][0], self.data_BB_verts[1][1], 5, fill_color="#ffaaaa")
        self.batch.add_circle(self.data_BB_verts[2][0], self.data_BB_verts[2][1], 5, fill_color="#ffaaaa")
        self.batch.add_circle(self.data_BB_verts[3][0], self.data_BB_verts[3][1], 5, fill_color="#ffaaaa")

        self.batch.add_text("Data BB", self.data_BB_verts[1][0] + 5, self.data_BB_verts[1][1] + 5, font_size=16, fill_color="#ffaaaa", anchor="lu")

    def set_ticks_bins(self, bins):
        self.target_bins_ticks = bins

    def set_plot_padding(self, plot_padding=10):
        self.plot_padding = plot_padding
        self.update_coords_mapping()

    def set_ticks_padding(self, ticks_padding):
        self.ticks_padding = ticks_padding

    def set_ticks_font_size(self, ticks_font_size):
        self.ticks_font_size = ticks_font_size

    def set_x_label(self, text=None, font_size=None, x_padding=None, y_padding=None, color=None):
        if text is not None:
            self.labels[0].text = text
        if font_size is not None:
            self.labels[0].font_size = font_size
        if x_padding is not None:
            self.labels[0].h_padding = x_padding
        if y_padding is not None:
            self.labels[0].v_padding = y_padding
        if color is not None:
            self.labels[0].color = color

    def set_y_label(self, text=None, font_size=None, x_padding=None, y_padding=None, color=None):
        if text is not None:
            self.labels[1].text = text
        if font_size is not None:
            self.labels[1].font_size = font_size
        if x_padding is not None:
            self.labels[1].h_padding = x_padding
        if y_padding is not None:
            self.labels[1].v_padding = y_padding
        if color is not None:
            self.labels[1].color = color

    def set_2y_label(self, text=None, font_size=None, x_padding=None, y_padding=None, color=None):
        if text is not None:
            self.labels[2].text = text
        if font_size is not None:
            self.labels[2].font_size = font_size
        if x_padding is not None:
            self.labels[2].h_padding = x_padding
        if y_padding is not None:
            self.labels[2].v_padding = y_padding
        if color is not None:
            self.labels[2].color = color

    def set_title(self, text=None, font_size=None, x_padding=None, y_padding=None, color=None):
        if text is not None:
            self.labels[3].text = text
        if font_size is not None:
            self.labels[3].font_size = font_size
        if x_padding is not None:
            self.labels[3].h_padding = x_padding
        if y_padding is not None:
            self.labels[3].v_padding = y_padding
        if color is not None:
            self.labels[3].color = color

    def set_data_BB(self, x=None, y=None, w=None, h=None):
        if x is not None:
            self.data_BB_xywh_normalized[0] = x
        if y is not None:
            self.data_BB_xywh_normalized[1] = y
        if w is not None:
            self.data_BB_xywh_normalized[2] = w
        if h is not None:
            self.data_BB_xywh_normalized[3] = h
        self.update_coords_mapping()

    def set_data_read_only(self, original_data):
        self.data_read_only = original_data.astype(np.float64)
        self.normalized_data = deepcopy(self.data_read_only)
        self.ticks_read_only = []
        self.normalized_ticks = []

        for channel in [0, 1]:
            ticks = self.get_ticks(self.normalized_data[:, channel], target_bins=self.target_bins_ticks[channel])
            self.ticks_read_only.append(deepcopy(ticks))

            min_value = np.min([np.min(ticks), np.min(self.normalized_data[:, channel])])
            max_value = np.max([np.max(ticks), np.max(self.normalized_data[:, channel])])

            delta_value = max_value - min_value

            self.normalized_data[:, channel] -= min_value
            self.normalized_data[:, channel] /= delta_value

            ticks -= min_value
            ticks /= delta_value

            self.normalized_ticks.append(ticks)

    def draw_data(self):

        if DRAW_DEBUG:
            self.draw_debug_info()

        for x, y in self.normalized_data:
            self.batch.add_circle(self.data_BB_verts[0][0] + x * (self.data_BB_xywh[2]), self.data_BB_verts[0][1] - y * (self.data_BB_xywh[3]), 5, "#94b1ff")

        for coord1, coord2 in zip(self.normalized_data[:-1, :], self.normalized_data[1:, :]):
            x1, y1, x2, y2 = *coord1, *coord2
            self.batch.add_line(self.data_BB_verts[0][0] + x1 * self.data_BB_xywh[2], self.data_BB_verts[0][1] - y1 * self.data_BB_xywh[3], self.data_BB_verts[0][0] + x2 * self.data_BB_xywh[2], self.data_BB_verts[0][1] - y2 * self.data_BB_xywh[3], stroke_color="#94b1ff", stroke_width=2)

        for channel in [0, 1]:
            ticks_coords = self.normalized_ticks[channel]
            ticks_labels = self.ticks_read_only[channel]

            if channel == 0:
                for label, coord in zip(ticks_labels, ticks_coords):
                    self.batch.add_text(label, self.data_BB_verts[0][0] + coord * (self.data_BB_xywh[2]), self.data_BB_verts[0][1] + self.ticks_padding[1], font_size=self.ticks_font_size[0], fill_color="#94b1ff", anchor="cu")

            elif channel == 1:
                for label, coord in zip(ticks_labels, ticks_coords):
                    self.batch.add_text(label, self.data_BB_verts[0][0] - self.ticks_padding[0], self.data_BB_verts[0][1] - coord * (self.data_BB_xywh[3]), font_size=self.ticks_font_size[1], fill_color="#94b1ff", anchor="cr")

        for label in self.labels:
            self.batch.add_text(label.text, self.plot_BB_xywh_padded[0] + label.pos[0].get_numerical_coord(), self.plot_BB_xywh_padded[1] + label.pos[1].get_numerical_coord(), font_size=label.font_size, fill_color=label.color, anchor=label.anchor, rotate=label.rotate)


    def get_ticks(self, array, target_bins=8) -> np.ndarray:
        vmin = np.min(array)
        vmax = np.max(array)

        if target_bins <= 0:
            raise ValueError("target_bins must be positive")

        delta = vmax - vmin

        # Degenerate case: all values equal
        if delta == 0:
            if vmin == 0:
                step = 1.0
            else:
                exponent = np.floor(np.log10(abs(vmin)))
                step = 10**exponent
            half = target_bins // 2
            return np.array([vmin + (i - half) * step for i in range(target_bins + 1)])

        raw_step = delta / target_bins

        exponent = np.floor(np.log10(abs(raw_step)))
        scale = 10**exponent
        normalized = raw_step / scale

        nice_values = [1, 2, 2.5, 5, 10]
        for val in nice_values:
            if normalized <= val:
                nice_multiplier = val
                break
        else:
            nice_multiplier = 10

        step = nice_multiplier * scale

        lower = np.floor(vmin / step) * step
        upper = np.ceil(vmax / step) * step

        n = int(round((upper - lower) / step))
        ticks = [lower + i * step for i in range(n + 1)]

        # refiniment left + right
        if (vmin - ticks[0]) > 0.33 * step:
            ticks.pop(0)

        if (ticks[-1] - vmax) > 0.33 * step:
            ticks.pop()

        return np.array(ticks)


class SVG_batch:
    def __init__(self):
        self.shapes: list[str] = []

    def add_rect(self, x, y, width, height, fill_color="#94b1ff", stroke_color="black"):
        self.shapes.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{fill_color}" stroke="{stroke_color}"/>')

    def add_circle(self, x, y, radius, fill_color="#94b1ff", stroke_color="black"):
        self.shapes.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill_color}" stroke="{stroke_color}"/>')

    def add_line(self, x1, y1, x2, y2, stroke_color="black", stroke_width=1):
        self.shapes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')

    def add_polygon(self, points, fill_color):
        points_str = " ".join([f"{i},{j}" for i, j in points])
        self.shapes.append(f'<polygon points="{points_str}" fill="{fill_color}"/>')

    def add_text(self, text, x, y, font_size=24, fill_color="black", anchor="cc", rotate=0):

        # For future implementations
        # X
        # "start" ---> left-aligned
        # "middle" ---> centered
        # "end" ---> right-aligned

        # Y
        # "hanging" ---> top-aligned
        # "middle" ---> vertically centered
        # "baseline" ---> default text baseline
        # "text-after-edge" ---> bottom-aligned

        text_anchor = ""
        dominant_baseline = ""

        match anchor:
            case 'lu': # left-up
                text_anchor = 'start'
                dominant_baseline = 'hanging'
            case 'cu': # center-up
                text_anchor = 'middle'
                dominant_baseline = 'hanging'
            case 'cc': # center-center
                text_anchor = 'middle'
                dominant_baseline = 'middle'
            case 'cr': # center-right
                text_anchor = 'end'
                dominant_baseline = 'middle'
            case 'cd': # center-down
                text_anchor = 'middle'
                dominant_baseline = 'text-after-edge'

        self.shapes.append(f'<text x="{x}" y="{y}" font-size="{font_size}" text-anchor="{text_anchor}" dominant-baseline="{dominant_baseline}" fill="{fill_color}" transform="rotate({rotate} {x} {y})">{text}</text>')


class Label:
    def __init__(self, 
        x, y, text, font_size, anchor, h_padding, v_padding, color, rotate=0) -> None:
        self.pos: list[DynamicCoordinate] = [x, y]
        self.text = text
        self.font_size = font_size
        self.h_padding = h_padding
        self.v_padding = v_padding
        self.color = color
        self.anchor = anchor
        self.rotate = rotate


class DynamicCoordinate:
    def __init__(self, coord: str) -> None:
        # %wtot ---> width screen
        # %htot ---> height screen
        # %w ---> width container
        # %h ---> height container
        # px ---> constant pixel amount
        self.coord = coord
        self.numerical_coord = 0
        self.coord_parsed = {
            "wtot" : 0,
            "htot" : 0,
            "w" : 0,
            "h" : 0,
            "px" : 0
        }
        self.coord_database = {
            "w_container" : 1,
            "h_container" : 1,
            "w_screen" : 1,
            "h_screen" : 1
        }


    def parser(self):

        self.coord_parsed = {
            "wtot" : 0,
            "htot" : 0,
            "w" : 0,
            "h" : 0,
            "px" : 0
        }

        instructions = self.coord.split()
        for instruction in instructions:
            if instruction.endswith("%wtot"):
                self.coord_parsed["wtot"] += float(instruction[:-5])
            if instruction.endswith("%htot"):
                self.coord_parsed["htot"] += float(instruction[:-5])
            if instruction.endswith("%w"):
                self.coord_parsed["w"] += float(instruction[:-2])
            if instruction.endswith("%h"):
                self.coord_parsed["h"] += float(instruction[:-2])
            if instruction.endswith("px"):
                self.coord_parsed["px"] += float(instruction[:-2])
            

    def get_numerical_coord(self):
        self.numerical_coord = 0
        for type, value in self.coord_parsed.items():
            if type == "w":
                self.numerical_coord += value * self.coord_database["w_container"]
            if type == "h":
                self.numerical_coord += value * self.coord_database["h_container"]
            if type == "wtot":
                self.numerical_coord += value * self.coord_database["w_screen"]
            if type == "htot":
                self.numerical_coord += value * self.coord_database["h_screen"]
            if type == "px":
                self.numerical_coord += value
        return self.numerical_coord


    def set_coord_database(self, w_container=None, h_container=None, w_screen=None, h_screen=None):
        if w_container is not None:
            self.coord_database['w_container'] = w_container
        if h_container is not None:
            self.coord_database['h_container'] = h_container
        if w_screen is not None:
            self.coord_database['w_screen'] = w_screen
        if h_screen is not None:
            self.coord_database['h_screen'] = h_screen


    def set_new_dynamic_coordinate(self, text):
        self.coord = text


if __name__ == "__main__":
    c = Canvas()
    c.set_image_size(1080, 1080)
    c.set_output_path("output.svg")

    c.plots_grid.set_grid_padding(10)

    c.plots_grid.add_plot("main1", [0, 0, c.width / 3, c.height / 3])
    c.plots_grid.plots["main1"].set_ticks_bins([4, 4])
    c.plots_grid.plots["main1"].set_ticks_padding([10, 10])
    c.plots_grid.plots["main1"].set_ticks_font_size([16, 16])
    c.plots_grid.plots["main1"].set_x_label(text="X [nm]", font_size=24)
    c.plots_grid.plots["main1"].set_y_label(text="Y [nm]", font_size=24)
    c.plots_grid.plots["main1"].set_title(text="Parabola", font_size=28)
    c.plots_grid.plots["main1"].set_data_read_only(np.array([[i, i**2] for i in range(21)]))
    c.plots_grid.plots["main1"].set_plot_padding(30)
    c.plots_grid.plots["main1"].set_data_BB(0.3, 0.2, 0.65, 0.65)

    c.plots_grid.add_plot("main2", [c.width / 3, 0, 2 * c.width / 3, c.height / 3])
    c.plots_grid.plots["main2"].set_ticks_bins([6, 4])
    c.plots_grid.plots["main2"].set_ticks_padding([15, 10])
    c.plots_grid.plots["main2"].set_ticks_font_size([18, 18])
    c.plots_grid.plots["main2"].set_x_label(text="X [nm]", font_size=24)
    c.plots_grid.plots["main2"].set_y_label(text="Y [nm]", font_size=24)
    c.plots_grid.plots["main2"].set_title(text="Cosine", font_size=28)
    c.plots_grid.plots["main2"].set_data_read_only(np.array([[i, np.sin(i / 3)] for i in range(51)]))
    c.plots_grid.plots["main2"].set_plot_padding(30)
    c.plots_grid.plots["main2"].set_data_BB(0.15, 0.2, 0.8, 0.65)

    c.plots_grid.add_plot("main3", [0, c.height / 3, c.width, 2 * c.height / 3])
    c.plots_grid.plots["main3"].set_ticks_bins([8, 10])
    c.plots_grid.plots["main3"].set_ticks_padding([20, 20])
    c.plots_grid.plots["main3"].set_ticks_font_size([24, 24])
    c.plots_grid.plots["main3"].set_data_read_only(np.array([[i, np.log(i + 0.1)] for i in range(21)]))
    c.plots_grid.plots["main3"].set_plot_padding(30)
    c.plots_grid.plots["main3"].set_data_BB(0.125, 0.2, 0.85, 0.65)

    c.save_image()
