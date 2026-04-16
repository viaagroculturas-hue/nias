import re

with open('nias.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the dead initOferta block: starts at "// OFERTA CHART (dead"
# and ends right before the second "function initOferta()" definition
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'dead Sankey code removed' in line:
        start_idx = i
    if start_idx and i > start_idx + 2 and line.strip().startswith('function initOferta()'):
        end_idx = i
        break

if start_idx and end_idx:
    # Find the "// OFERTA CHART" comment just before the real initOferta
    # We want to keep lines from end_idx-2 onward (the comment block)
    # Remove lines from start_idx to end_idx-3 (the dead code)
    # But first, find where the dead code actually starts (the orphaned L1=[...])
    print(f'Dead code region: line {start_idx+1} to {end_idx+1}')
    print(f'Removing lines {start_idx+1} to {end_idx-1}')
    # Keep the "// OFERTA CHART" header and the real function
    new_lines = lines[:start_idx] + ['\n'] + lines[end_idx-2:]
    with open('nias.html', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f'Done. Was {len(lines)} lines, now {len(new_lines)} lines')
else:
    print(f'start_idx={start_idx}, end_idx={end_idx} — not found')
