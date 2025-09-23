import tkinter as tk
from tkinter import filedialog, messagebox
import math
import os
from PIL import Image, ImageDraw, ImageTk
import re


class RasterizationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Инструмент растрирования SVG")
        self.root.geometry("1300x700")

        self.svg_content = ""
        self.segments = []
        self.images = {}
        self.zigzag_points = []
        self.svg_width = 0
        self.svg_height = 0

        self.create_widgets()

    def create_widgets(self):
        left_frame = tk.Frame(self.root, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        svg_label = tk.Label(left_frame, text="Содержимое SVG файла:")
        svg_label.pack(anchor=tk.W)

        self.svg_text = tk.Text(left_frame, height=10, width=45)
        self.svg_text.pack(fill=tk.X, pady=(0, 10))

        button_frame = tk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=5)

        open_btn = tk.Button(button_frame, text="Открыть SVG файл", command=self.open_svg)
        open_btn.pack(side=tk.LEFT, padx=(0, 5))

        build_btn = tk.Button(button_frame, text="Построить зигзаги", command=self.build_zigzag_images)
        build_btn.pack(side=tk.LEFT, padx=5)

        save_btn = tk.Button(button_frame, text="Сохранить все в png и ppm", command=self.save_all_images)
        save_btn.pack(side=tk.LEFT, padx=5)

        zigzag_frame = tk.LabelFrame(left_frame, text="Параметры зигзага")
        zigzag_frame.pack(fill=tk.X, pady=10)

        tk.Label(zigzag_frame, text="Угол:").grid(row=0, column=0, sticky=tk.W)
        self.angle_var = tk.StringVar(value="")
        tk.Entry(zigzag_frame, textvariable=self.angle_var).grid(row=0, column=1, sticky=tk.W)

        tk.Label(zigzag_frame, text="Звенья:").grid(row=1, column=0, sticky=tk.W)
        self.links_var = tk.StringVar(value="")
        tk.Entry(zigzag_frame, textvariable=self.links_var).grid(row=1, column=1, sticky=tk.W)

        svg_canvas_frame = tk.LabelFrame(left_frame, text="Исходный SVG файл")
        svg_canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.svg_canvas = tk.Canvas(svg_canvas_frame, bg='white', height=200)
        self.svg_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas_frame = tk.Frame(right_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvases = {}
        self.labels = {}
        self.scrollbars = {}

        algorithms = ["dda", "bresenham", "int_bresenham", "builtin"]
        algorithm_names = {
            "dda": "Алгоритм ЦДА",
            "bresenham": "Алгоритм Брезенхема",
            "int_bresenham": "Целочисленный Брезенхем",
            "builtin": "Встроенные средства языка программирования"
        }

        for i, algo in enumerate(algorithms):
            frame = tk.Frame(self.canvas_frame)
            frame.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="nsew")

            self.canvas_frame.grid_rowconfigure(i // 2, weight=1)
            self.canvas_frame.grid_columnconfigure(i % 2, weight=1)

            label = tk.Label(frame, text=algorithm_names[algo], font=("Arial", 10, "bold"))
            label.pack()
            self.labels[algo] = label

            canvas_container = tk.Frame(frame)
            canvas_container.pack(fill=tk.BOTH, expand=True)

            canvas = tk.Canvas(canvas_container, bg='white')
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            v_scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=canvas.yview)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=canvas.xview)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            self.canvases[algo] = canvas
            self.scrollbars[algo] = (v_scrollbar, h_scrollbar)

    def open_svg(self):
        file_path = filedialog.askopenfilename(filetypes=[("SVG files", "*.svg"), ("Все файлы", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.svg_content = file.read()
                    self.svg_text.delete(1.0, tk.END)
                    self.svg_text.insert(tk.END, self.svg_content)
                    self.parse_svg()
                    self.display_svg_preview()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")

    def parse_svg(self):
        self.segments = []

        width_match = re.search(r'width="([\d.]+)"', self.svg_content)
        height_match = re.search(r'height="([\d.]+)"', self.svg_content)

        if width_match and height_match:
            self.svg_width = float(width_match.group(1))
            self.svg_height = float(height_match.group(1))
        else:
            self.svg_width = 400
            self.svg_height = 300

        lines = self.svg_content.split('\n')
        for line in lines:
            if 'line' in line and 'x1=' in line:
                try:
                    x1 = float(re.search(r'x1="([\d.]+)"', line).group(1))
                    y1 = float(re.search(r'y1="([\d.]+)"', line).group(1))
                    x2 = float(re.search(r'x2="([\d.]+)"', line).group(1))
                    y2 = float(re.search(r'y2="([\d.]+)"', line).group(1))
                    self.segments.append(((x1, y1), (x2, y2)))
                except:
                    continue

    def display_svg_preview(self):
        self.svg_canvas.delete("all")

        if not self.segments:
            return

        canvas_width = self.svg_canvas.winfo_width()
        canvas_height = self.svg_canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width, canvas_height = 300, 200

        padding = 20

        all_points = []
        for segment in self.segments:
            all_points.extend(segment)

        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)

        width = max_x - min_x
        height = max_y - min_y

        if width > 0 and height > 0:
            scale_x = (canvas_width - 2 * padding) / width
            scale_y = (canvas_height - 2 * padding) / height
            scale = min(scale_x, scale_y)
        else:
            scale = 1

        for segment in self.segments:
            x1, y1 = segment[0]
            x2, y2 = segment[1]

            x1_scaled = padding + (x1 - min_x) * scale
            y1_scaled = padding + (y1 - min_y) * scale
            x2_scaled = padding + (x2 - min_x) * scale
            y2_scaled = padding + (y2 - min_y) * scale

            self.svg_canvas.create_line(x1_scaled, y1_scaled, x2_scaled, y2_scaled, fill="black", width=2)

    def dda_algorithm(self, x1, y1, x2, y2):
        points = []
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))

        if steps == 0:
            return [(int(x1), int(y1))]

        x_increment = dx / steps
        y_increment = dy / steps

        x, y = x1, y1
        for _ in range(int(steps) + 1):
            points.append((int(round(x)), int(round(y))))
            x += x_increment
            y += y_increment

        return points

    def bresenham_algorithm(self, x1, y1, x2, y2):
        points = []
        x1, y1, x2, y2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steep = dy > dx

        if steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
            dx, dy = dy, dx

        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1

        dx = x2 - x1
        dy = abs(y2 - y1)
        error = dx / 2
        y = y1
        ystep = 1 if y1 < y2 else -1

        for x in range(x1, x2 + 1):
            coord = (y, x) if steep else (x, y)
            points.append(coord)
            error -= dy
            if error < 0:
                y += ystep
                error += dx

        return points

    def integer_bresenham_algorithm(self, x1, y1, x2, y2):
        points = []
        x1, y1, x2, y2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steep = dy > dx

        if steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
            dx, dy = dy, dx

        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1

        dx = x2 - x1
        dy = abs(y2 - y1)
        error = 0
        y = y1
        ystep = 1 if y1 < y2 else -1

        for x in range(x1, x2 + 1):
            coord = (y, x) if steep else (x, y)
            points.append(coord)
            error += dy
            if 2 * error >= dx:
                y += ystep
                error -= dx

        return points

    def draw_segment(self, draw, start, end, algorithm):
        x1, y1 = start
        x2, y2 = end

        if algorithm == "dda":
            points = self.dda_algorithm(x1, y1, x2, y2)
        elif algorithm == "bresenham":
            points = self.bresenham_algorithm(x1, y1, x2, y2)
        elif algorithm == "int_bresenham":
            points = self.integer_bresenham_algorithm(x1, y1, x2, y2)
        else:  # built-in
            draw.line([(x1, y1), (x2, y2)], fill="black", width=1)
            return

        for point in points:
            draw.point(point, fill="black")

    def build_zigzag_images(self):
        if not self.segments:
            messagebox.showwarning("Предупреждение", "В SVG файле не найдено сегментов!")
            return

        try:
            angle = float(self.angle_var.get())
            links = int(self.links_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Неверное значение угла или количества звеньев!")
            return

        self.zigzag_points = []
        for segment in self.segments:
            x1, y1 = segment[0]
            x2, y2 = segment[1]

            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            original_angle = math.atan2(y2 - y1, x2 - x1)

            zigzag_length = length / links
            zigzag_angle = math.radians(angle)

            points = [(x1, y1)]
            current_x, current_y = x1, y1

            for i in range(links):
                current_angle = original_angle + zigzag_angle if i % 2 == 0 else original_angle - zigzag_angle

                next_x = current_x + zigzag_length * math.cos(current_angle)
                next_y = current_y + zigzag_length * math.sin(current_angle)

                points.append((next_x, next_y))
                current_x, current_y = next_x, next_y

            self.zigzag_points.append(points)

        all_points = []
        for points in self.zigzag_points:
            all_points.extend(points)

        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)

        padding = 20
        width = int(max_x - min_x + 2 * padding)
        height = int(max_y - min_y + 2 * padding)

        algorithms = ["dda", "bresenham", "int_bresenham", "builtin"]

        for algo in algorithms:
            image = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(image)

            for points in self.zigzag_points:
                for i in range(len(points) - 1):
                    start = (points[i][0] - min_x + padding, points[i][1] - min_y + padding)
                    end = (points[i + 1][0] - min_x + padding, points[i + 1][1] - min_y + padding)
                    self.draw_segment(draw, start, end, algo)

            self.images[algo] = image

        self.display_all_images()

    def display_all_images(self):
        for algo, canvas in self.canvases.items():
            if algo in self.images:
                canvas.delete("all")

                image = self.images[algo]

                photo = ImageTk.PhotoImage(image)

                canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                canvas.image = photo

                canvas.configure(scrollregion=canvas.bbox(tk.ALL))

    def save_all_images(self):
        if not self.images:
            messagebox.showwarning("Предупреждение", "Нет изображений для сохранения!")
            return

        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        try:
            for algo, image in self.images.items():
                png_path = os.path.join(folder_path, f"{algo}.png")
                image.save(png_path)

                ppm_path = os.path.join(folder_path, f"{algo}.ppm")
                self.save_ppm(image, ppm_path)

            messagebox.showinfo("Успех", f"Все изображения сохранены в: {folder_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить изображения: {str(e)}")

    def save_ppm(self, image, file_path):
        rgb_image = image.convert("RGB")
        width, height = rgb_image.size
        pixels = rgb_image.load()

        with open(file_path, 'w') as f:
            f.write("P3\n")
            f.write(f"{width} {height}\n")
            f.write("255\n")

            for y in range(height):
                row = []
                for x in range(width):
                    r, g, b = pixels[x, y]
                    row.extend([str(r), str(g), str(b)])
                f.write(" ".join(row) + "\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = RasterizationApp(root)
    root.mainloop()