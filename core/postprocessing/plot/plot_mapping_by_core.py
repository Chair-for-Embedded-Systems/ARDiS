from matplotlib import pyplot as plt

def plot_mapping_by_core(output_file: str,
                         data: dict[str, list[tuple[int, float, float]]], # app -> [core, start, end]
                         verbose: bool = False):
    
    if verbose:
        print(f"Plotting {output_file}") 

    used_cores = {core for _, core_range in data.items() for core, _, _ in core_range}
    used_cores = [core for core in used_cores]
    used_cores.sort(reverse=True)
    
    core_to_y = {core: index for index, core in enumerate(used_cores)}

    fig, axis = plt.subplots(layout='constrained',figsize=(8,len(used_cores) * 0.25))
    axis.set_title("Application to core mapping for multiple apps")    
    for app, core_ranges in data.items():
        core, start, end = zip(*core_ranges)
        core, start, end = list(core), list(start), list(end)
        width = [e_i - s_i for s_i,e_i in zip(start, end)]
        #for core, start, end in core_ranges:
        axis.barh(y = [core_to_y[c] for c in core], width=width, height=0.8, left=start, label=app)
    
    core, y = zip(*core_to_y.items())
    axis.set_yticks(ticks=y, labels=core)

    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Core Id")
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), borderaxespad=2.5, ncol=4)
    axis.set_axisbelow(True)
    axis.grid(True, axis='y', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)
    plt.savefig(output_file, dpi=300, format='png', bbox_inches='tight')
    plt.close() 