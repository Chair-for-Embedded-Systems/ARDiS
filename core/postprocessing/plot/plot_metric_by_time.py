import matplotlib.pyplot as plt
from pandas import Series

def plot_app_metric_by_time(output_file: str,
                            data: dict[str, tuple[Series, Series]], # app -> (x, y)
                            title: str,
                            x_label: str,
                            y_label: str,
                            y_unit_size: int = 1,
                            verbose: bool = False):
    if verbose:
        print(f"Plotting {output_file}") 
    
    fig, axis = plt.subplots(figsize=(8,4))
    axis.set_title(f"{title}")
    for app, (x,y) in data.items():
        if y_unit_size > 1:
            y = y / y_unit_size
        axis.plot(x, y, label=app)

    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), borderaxespad=2.5, ncol=4)

    axis.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)
    plt.savefig(output_file, dpi=300, format='png', bbox_inches='tight')
    plt.close() 