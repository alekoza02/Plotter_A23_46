from time import perf_counter_ns

class Canvas:
    def __init__(self):
        self.aspect_ratio: float
        self.width: int
        self.height: int

        self.plots_grid: Grid = Grid()

        self.output_path: str


    def __set_aspect_ratio(self, aspect_ratio=1):
        self.aspect_ratio = aspect_ratio


    def set_image_size(self, width, height):
        self.width = width
        self.height = height
        self.__set_aspect_ratio(self.width / self.height)

        self.plots_grid.set_padding(min(self.width, self.height) / 100)


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

        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(HEADER)
            for shape in self.plots_grid.batch:
                f.write("  " + shape + "\n")
            f.write(FOOTER)
        
        stop_timer = perf_counter_ns()
        print(f"Saving took: {(stop_timer - start_timer) / 1e6:.1f}ms")
        print(f"Which means this could update around {1 / ((stop_timer - start_timer) / 1e9):.1f} times a second")




class Grid():
    def __init__(self):
        self.padding = 15
        self.IDs: set[str] = set()
        self.BBs: dict[str, list[int]] = {}
        self.plots: dict[str, Plot] = {}


    def set_padding(self, padding=10):
        self.padding = padding


    def add_plot(self, id, BB):
        self.IDs.add(id)
        self.BBs[id] = BB
        self.plots[id] = Plot()

        self.plots[id].batch.add_circle(BB[0] + self.padding, BB[1] + self.padding, 10)
        self.plots[id].batch.add_circle(BB[0] + self.padding, BB[1] + BB[3] - self.padding, 10)
        self.plots[id].batch.add_circle(BB[0] + BB[2] - self.padding, BB[1] + self.padding, 10)
        self.plots[id].batch.add_circle(BB[0] + BB[2] - self.padding, BB[1] + BB[3] - self.padding, 10)
        
        self.plots[id].batch.add_line(BB[0] + self.padding, BB[1] + self.padding, BB[0] + self.padding, BB[1] + BB[3] - self.padding, stroke_color='#94b1ff', stroke_width=5)
        self.plots[id].batch.add_line(BB[0] + self.padding, BB[1] + self.padding, BB[0] + BB[2] - self.padding, BB[1] + self.padding, stroke_color='#94b1ff', stroke_width=5)
        self.plots[id].batch.add_line(BB[0] + BB[2] - self.padding, BB[1] + BB[3] - self.padding, BB[0] + self.padding, BB[1] + BB[3] - self.padding, stroke_color='#94b1ff', stroke_width=5)
        self.plots[id].batch.add_line(BB[0] + BB[2] - self.padding, BB[1] + BB[3] - self.padding, BB[0] + BB[2] - self.padding, BB[1] + self.padding, stroke_color='#94b1ff', stroke_width=5)

        self.plots[id].batch.add_text(f"Plot: {id}", BB[0] + BB[2] / 2, BB[1] + BB[3] / 2, font_size=48, fill_color='#94b1ff')


    @property
    def batch(self):
        ris = [shape for plot in self.plots.values() for shape in plot.batch.shapes]
        return ris



class Plot():
    def __init__(self):
        self.batch = SVG_batch()



class SVG_batch():
    def __init__(self):
        self.shapes: list[str] = []


    def add_rect(self, x, y, width, height, fill_color='#dc143c', stroke_color='black'):
        self.shapes.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{fill_color}" stroke="{stroke_color}"/>')


    def add_circle(self, x, y, radius, fill_color='#94b1ff', stroke_color='black'):
        self.shapes.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill_color}" stroke="{stroke_color}"/>')


    def add_line(self, x1, y1, x2, y2, stroke_color='black', stroke_width=1):
        self.shapes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>',)


    def add_polygon(self, points, fill_color):
        points_str = " ".join([f"{i},{j}" for i, j in points])
        self.shapes.append(f'<polygon points="{points_str}" fill="{fill_color}"/>',)


    def add_text(self, text, x, y, font_size=24, fill_color='black'):
        self.shapes.append(f'<text x="{x}" y="{y}" font-size="{font_size}" text-anchor="middle" dominant-baseline="middle" fill="{fill_color}">{text}</text>')



if __name__ == "__main__":

    c = Canvas()
    c.set_image_size(1080, 1080)
    c.set_output_path('output.svg')
    c.plots_grid.add_plot('main1', [0, 0, c.width / 3, c.height / 3])
    c.plots_grid.add_plot('main2', [c.width / 3, 0, 2 * c.width / 3, c.height / 3])
    c.plots_grid.add_plot('main3', [0, c.height / 3, c.width, 2 * c.height / 3])
    c.save_image()