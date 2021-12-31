import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib import ticker as mticker
import numpy as np
import requests

from libs.cli import Cli
from libs.path import Path
from libs.progressbar import ProgressBar
from libs.threading import Threads


class Visualizer:
    def __init__(self, args):
        self.args = args
        self.output_folder = args.output_folder or Path.docs / "Other" / Path(__file__).parent.name
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.data_items = {
            "tests": {"cases": "TESTS_ALL_POS"},
            "HOSP": {"hospitalisations": "NEW_IN", "ICU": "TOTAL_IN_ICU"}
            }
        self.data = {}
        
    def visualize(self):
        with ProgressBar("Corona"):
            self.start_visualization()

    def get_data(self, name):
        url = f"https://epistat.sciensano.be/Data/COVID19BE_{name}.json"
        r = requests.get(url)
        self.data[name] = json.loads(r.content) if r.status_code == 200 else None

    def start_visualization(self):
        Threads(self.get_data, self.data_items.keys()).join()
        
        for data_name, data_info in self.data_items.items():
            for title, key in data_info.items():
                if self.data[data_name] is not None:
                    data = self.parse_dict(self.data[data_name], key)
                    self.make_visualization(title, data)
                else:
                    print(f"{title} not available")
        
        self.open_visualizations()
                    
    def open_visualizations(self):
        urls = [
            *(
                str((self.output_folder / title).with_suffix(".html")) for data_item in self.data_items.values() for title in data_item
            ),
            "https://covid-19.sciensano.be/sites/default/files/Covid19/Meest%20recente%20update.pdf",
            "https://covid-vaccinatie.be/en",
        ]
        command = " ".join(["chromium"] + urls)
        Cli.run(command, wait=False)

    def make_visualization(self, title, values):
        x = list(values.keys())
        y = list(values.values())
        y_avg = get_averages(y)

        ratio = y_avg[-4] / y_avg[-11]
        change = round((ratio - 1) * 100)
        last_value = int(y_avg[-4])
        change_str = f"+ {change}%" if change > 0 else f" - {-change}%"
        fig_title = f"{title.capitalize()}: {last_value} ({change_str})"
        
        plt.switch_backend('agg') # needed because matplotlib runs in thread
        fig, ax = plt.subplots(figsize=(19, 9))
        
        ax.set_title(fig_title, fontsize=16)
        ax.semilogy(x, y, color='green', linewidth=0.5)
        ax.semilogy(x, y_avg, color='black', linewidth=3)
        for index in [-4, -11]:
            ax.plot(x[index], y_avg[index], marker='o', markersize=6, color="red")
            
        formatter = mticker.ScalarFormatter()
        ax.yaxis.set_major_formatter(formatter)
        ax.yaxis.set_minor_formatter(formatter)
        ax.grid(axis="y")

        output_file = (self.output_folder / title).with_suffix(".png")
        fig.savefig(output_file)
        output_file.with_suffix(".html").write_text(
            f'<img src="{title}.png" style="width:100%">'
        )


    def parse_dict(self, data, key):
        date_format = '%Y-%m-%d'
        start_date = datetime.strptime(self.args.start_date, date_format)
        today = datetime.today()
        update_intervals = {
            0: 4,
            6: 3
            }
        update_interval = (
            update_intervals.get(today.weekday(), 2) 
            if key == "TESTS_ALL_POS" 
            else 0 # hospitals updated immediately
        )
        now = today - timedelta(days=update_interval+1)
    
        parsed_dict = {}
        for sample in data:
            date = datetime.strptime(sample["DATE"], date_format)
            if start_date < date < now:
                if self.args.province is None or sample.get("PROVINCE") == args.province:
                    parsed_dict[date] = parsed_dict.get(date, 0) + sample[key] # accumulate data from various locations
                    
        parsed_dict = {k: v for k, v in parsed_dict.items() if v > 0}
        return parsed_dict


def get_averages(items, N=7):
    running_average_filter = np.ones(N) / N
    means = np.convolve(items, running_average_filter, mode='valid')
    
    missing_size = (N - 1) // 2
    head = np.ones(missing_size) * means[0]
    tail = np.ones(missing_size) * means[-1]
    means = np.concatenate((head, means, tail))
    
    return means
