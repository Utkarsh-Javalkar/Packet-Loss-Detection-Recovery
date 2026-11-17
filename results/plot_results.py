"""Create comparison charts from measured results/data/performance.csv."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
source = ROOT / 'data' / 'performance.csv'
out = ROOT / 'graphs'
out.mkdir(parents=True, exist_ok=True)
if not source.exists():
    raise SystemExit(f'Missing {source}. Copy performance_template.csv and fill only measured values.')
with source.open(newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit('No measured rows found; refusing to generate empty charts.')
profiles = ['light', 'medium', 'heavy']
for metric, ylabel, filename in [
    ('measured_network_loss_pct', 'Measured network loss (%)', 'network_loss.png'),
    ('goodput_mbps', 'Goodput (Mbps)', 'goodput.png'),
]:
    fig, ax = plt.subplots()
    modes = sorted({r['mode'] for r in rows})
    for mode in modes:
        selected = [r for r in rows if r['mode'] == mode]
        values = []
        labels = []
        for profile in profiles:
            hit = next((r for r in selected if r['profile'] == profile), None)
            if hit is not None and hit.get(metric, '') != '':
                labels.append(profile)
                values.append(float(hit[metric]))
        if values:
            ax.plot(labels, values, marker='o', label=mode)
    ax.set_xlabel('Loss profile')
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel + ' by profile')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / filename, dpi=160)
    plt.close(fig)
print(f'Charts saved in {out}')
