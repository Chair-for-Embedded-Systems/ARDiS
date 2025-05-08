from matplotlib import pyplot as plt

def plot_apps_by_mapped_core(output_file: str,
                         data: dict[str, list[tuple[int, float, float]]], # app -> [(core, start, end)]
                         verbose: bool = False):
    
    if verbose:
        print(f"Plotting {output_file}") 

    # Check which cores need to be shown
    used_cores = {core for _, core_range in data.items() for core, _, _ in core_range}
    used_cores = [core for core in used_cores]
    
    # Create a mapping for core_id -> y 
    used_cores.sort(reverse=True) # Lowest core should be placed on top of the y axis
    core_to_y = {core: index for index, core in enumerate(used_cores)}

    fig, axis = plt.subplots(figsize=(8,len(used_cores) * 0.2 + 1))
    axis.set_title("Application to core mapping for multiple apps")    
    for app, core_ranges in data.items():
        core, start, end = zip(*core_ranges)
        core, start, end = list(core), list(start), list(end)
        
        y = [core_to_y[c] for c in core]
        width = [e_i - s_i for s_i,e_i in zip(start, end)]
        
        axis.barh(y = y, width=width, height=0.8, left=start, label=app)
    
    core, y = zip(*core_to_y.items())
    core = [f"Core {c}" for c in core]
    axis.set_yticks(ticks=y, labels=core)

    axis.set_xlabel("Time (s)")
    axis.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    axis.set_axisbelow(True)
    axis.grid(True, axis='y', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)
    plt.savefig(output_file, dpi=300, format='png', bbox_inches='tight')
    plt.close() 