from datetime import datetime, timedelta

import cli
import downloader
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker as mticker
from plib import Path as BasePath


class Path(BasePath):
    output = BasePath.assets / "corona"

    @staticmethod
    def output_file(title, suffix=".html"):
        return (Path.output / title).with_suffix(suffix)


class Visualizer:
    def __init__(self, args):
        self.args = args

    def visualize(self):
        data_items = {
            "tests": {"cases": "TESTS_ALL_POS"},
            "HOSP": {"hospitalisations": "NEW_IN", "ICU": "TOTAL_IN_ICU"},
        }
        urls = [
            f"https://epistat.sciensano.be/Data/COVID19BE_{name}.json"
            for name in data_items.keys()
        ]
        dests = downloader.download_urls(urls, folder=Path.output)
        for dest in dests:
            pass  # disable for now
            # new versions only have additional content at the end instead of closing ']'
            # dest.with_suffix(dest.suffix + ".part").text = dest.text[:-5000]

        for data_info, dest in zip(data_items.values(), dests):
            for title, key in data_info.items():
                data = self.load_data(dest, key)
                Visualizer.make_visualization(title, data)

        output_files = [
            Path.output_file(title)
            for data_item in data_items.values()
            for title in data_item
        ]
        Visualizer.open_visualizations(output_files)

    @staticmethod
    def open_visualizations(output_files):
        urls = [
            *output_files,
            "https://covid-19.sciensano.be/sites/default/files/Covid19/Meest%20recente%20update.pdf",
            "https://covid-vaccinatie.be/en",
        ]
        try:
            cli.start("chromium", urls)
        except FileNotFoundError:
            cli.urlopen(*urls)

    @staticmethod
    def make_visualization(title, values):
        x = list(values.keys())
        y = list(values.values())
        y_avg = get_averages(y)

        ratio = y_avg[-4] / y_avg[-11]
        change = round((ratio - 1) * 100)
        last_value = int(y_avg[-4])
        change_str = f"+ {change}%" if change > 0 else f" - {-change}%"
        fig_title = f"{title.capitalize()}: {last_value} ({change_str})"

        plt.switch_backend("agg")  # needed because matplotlib runs in thread
        fig, ax = plt.subplots(figsize=(19, 9))

        ax.set_title(fig_title, fontsize=16)
        ax.semilogy(x, y, color="green", linewidth=0.5)
        ax.semilogy(x, y_avg, color="black", linewidth=3)
        for index in [-4, -11]:
            ax.plot(x[index], y_avg[index], marker="o", markersize=6, color="red")

        formatter = mticker.ScalarFormatter()
        ax.yaxis.set_major_formatter(formatter)
        ax.yaxis.set_minor_formatter(formatter)
        ax.grid(axis="y")

        filename = Path.output_file(title, suffix=".png")
        fig.savefig(filename)
        Path.output_file(title).write_text(
            f'<img src="{filename.name}" style="width:100%">'
        )

    def load_data(self, name, key):
        data = (Path.output / name).json

        date_format = "%Y-%m-%d"
        start_date = datetime.strptime(self.args.start_date, date_format)
        today = datetime.today()
        # update_intervals = {0: 4, 6: 3}
        """update_interval = (
            update_intervals.get(today.weekday(), 2)
            if key == "TESTS_ALL_POS"
            else 0  # hospitals updated immediately
        )"""
        update_interval = 0
        now = today - timedelta(days=update_interval + 1)

        parsed_dict = {}
        for sample in data:
            date = datetime.strptime(sample["DATE"], date_format)
            if start_date < date < now:
                if (
                    self.args.province is None
                    or sample.get("PROVINCE") == args.province
                ):
                    parsed_dict[date] = (
                        parsed_dict.get(date, 0) + sample[key]
                    )  # accumulate data from all regions

        parsed_dict = {k: v for k, v in parsed_dict.items() if v > 0}
        parsed_dict = self.check_abnormal_changes(parsed_dict)
        return parsed_dict

    @classmethod
    def check_abnormal_changes(cls, info_dict):
        values = list(info_dict.values())

        while len(values) > 8 and values[-8] / values[-1] > 10:
            keys = list(info_dict.keys())
            info_dict.pop(keys[-1])
            values = list(info_dict.values())

        return info_dict


def get_averages(items, N=7):
    running_average_filter = np.ones(N) / N
    means = np.convolve(items, running_average_filter, mode="valid")

    missing_size = (N - 1) // 2
    head = np.ones(missing_size) * means[0]
    tail = np.ones(missing_size) * means[-1]
    means = np.concatenate((head, means, tail))

    return means
