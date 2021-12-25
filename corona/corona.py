import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib import ticker as mticker
import numpy as np
import requests
import sys

from libs.cli import Cli
from libs.errorhandler import ErrorHandler
from libs.path import Path
from libs.progressbar import ProgressBar
from libs.threading import Threads

output_folder = Path(__file__).parent.parent / "assets"
output_folder.mkdir(parents=True, exist_ok=True)

def get_dict(data, key):
    start_date = "2020-11-1"
    start_date = "2020-09-1"
    #start_date = "2020-03-1"
    #start_date = "2020-12-1"

    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    today = datetime.today()
    updates = {
        0: 4,
        6: 3
        }
    last_update = updates.get(today.weekday(), 2)
    now = today - timedelta(days=last_update)
    
    dic = {}
    for d in data:
        if "flanders" not in sys.argv or key != "TESTS_ALL_POS" or d.get("PROVINCE", 0) == "WestVlaanderen":
            date = datetime.strptime(d["DATE"], '%Y-%m-%d')
            if date not in dic:
                dic[date] = 0
            dic[date] += d[key]
            
    new_dic = {k: v for k, v in dic.items() if v and k > start_date and (k < now or key != "TESTS_ALL_POS")}
    return new_dic


def get_data(name, key):
    url = f"https://epistat.sciensano.be/Data/COVID19BE_{name}.json"
    r = requests.get(url)
    if r.status_code == 200:
        data = json.loads(r.content)
        data = get_dict(data, key)
    else:
        data = None
    return data


def get_averages(items, N=7):
    running_average_filter = np.ones(N) / N
    means = np.convolve(items, running_average_filter, mode='valid')
    
    missing_size = (N - 1) // 2
    head = np.ones(missing_size) * means[0]
    tail = np.ones(missing_size) * means[-1]
    means = np.concatenate((head, means, tail))
    
    return means

def show(title, names):
    values = get_data(*names)
    if not values:
        print(f"{names[0]} not available")
        return
        
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

    output_file = (output_folder / title).with_suffix(".png")
    fig.savefig(output_file)
    output_file.with_suffix(".html").write_text(
        f'<img src="{title}.png" style="width:100%">'
    )


def show_all():
    datas = {
        "cases": ("tests", "TESTS_ALL_POS"),
        "hospitalisations": ("HOSP", "NEW_IN")
        }
    Threads(show, datas.keys(), datas.values()).join()
        
    urls = [
        *(
            str((output_folder / title).with_suffix(".html")) for title in datas
        ),
        "https://covid-19.sciensano.be/sites/default/files/Covid19/Meest%20recente%20update.pdf",
        "https://covid-vaccinatie.be/en",
    ]
    command = " ".join(["chromium"] + urls)
    Cli.run(command, wait=False)
        

def main():
    with ProgressBar("Corona", "Updating.."), ErrorHandler():
        show_all()

if __name__ == "__main__":
    main()
