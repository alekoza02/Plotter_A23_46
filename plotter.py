from copy import deepcopy
from time import perf_counter_ns

import numpy as np
import numpy.typing as npt


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

    def set_grid_padding(self, grid_padding: float = 10):
        self.grid_padding = grid_padding

    def add_plot(self, id, BB):
        self.IDs.add(id)

        BB_padding = [BB[0] + self.grid_padding, BB[1] + self.grid_padding, BB[2] - 2 * self.grid_padding, BB[3] - 2 * self.grid_padding]

        self.BBs[id] = BB_padding
        self.plots[id] = Plot(id, BB_padding[0], BB_padding[1], BB_padding[2], BB_padding[3])

    @property
    def batch(self):
        ris = [shape for plot in self.plots.values() for shape in plot.batch.shapes]
        return ris


class Plot:
    def __init__(self, id, x, y, width, height):
        self.id = id

        self.ticks_padding = [7, 7]
        self.ticks_font_size = [16, 16]
        self.plot_padding = 15

        self.target_bins_ticks = [8, 8]

        self.data_BB_xywh_normalized: list[float] = [0.2, 0.2, 0.775, 0.65]
        self.plot_BB_xywh_original = [x, y, width, height]

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

    def add_text(self, text, x, y, font_size=24, fill_color="black", anchor="cc"):

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

        self.shapes.append(f'<text x="{x}" y="{y}" font-size="{font_size}" text-anchor="{text_anchor}" dominant-baseline="{dominant_baseline}" fill="{fill_color}">{text}</text>')


if __name__ == "__main__":
    c = Canvas()
    c.set_image_size(1080, 1080)
    c.set_output_path("output.svg")

    c.plots_grid.set_grid_padding(10)

    c.plots_grid.add_plot("main1", [0, 0, c.width / 3, c.height / 3])
    c.plots_grid.plots["main1"].set_ticks_bins([4, 4])
    c.plots_grid.plots["main1"].set_ticks_padding([10, 10])
    c.plots_grid.plots["main1"].set_ticks_font_size([16, 16])
    c.plots_grid.plots["main1"].set_data_read_only(np.array([[i, i**2] for i in range(21)]))
    c.plots_grid.plots["main1"].set_plot_padding(30)

    c.plots_grid.add_plot("main2", [c.width / 3, 0, 2 * c.width / 3, c.height / 3])
    c.plots_grid.plots["main2"].set_ticks_bins([6, 4])
    c.plots_grid.plots["main2"].set_ticks_padding([15, 10])
    c.plots_grid.plots["main2"].set_ticks_font_size([18, 18])
    c.plots_grid.plots["main2"].set_data_read_only(np.array([[i, np.sin(i / 3)] for i in range(51)]))
    c.plots_grid.plots["main2"].set_plot_padding(30)

    c.plots_grid.add_plot("main3", [0, c.height / 3, c.width, 2 * c.height / 3])
    c.plots_grid.plots["main3"].set_ticks_bins([8, 10])
    c.plots_grid.plots["main3"].set_ticks_padding([20, 20])
    c.plots_grid.plots["main3"].set_ticks_font_size([24, 24])
    c.plots_grid.plots["main3"].set_data_read_only(np.array([[i, np.log(i + 0.1)] for i in range(21)]))
    c.plots_grid.plots["main3"].set_plot_padding(30)

    c.save_image()
