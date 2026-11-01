path = '/c/Users/ESPRIEAETHER/Desktop/esprieaether/.env'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('OKX_API_KEY='):
        new_lines.append('OKX_API_KEY=\n')
    elif line.startswith('OKX_SECRET_KEY='):
        new_lines.append('OKX_SECRET_KEY=\n')
    elif line.startswith('OKX_PASS='):
        new_lines.append("OKX_PASS=Trading d'API\n")
    else:
        new_lines.append(line)

with open(path, 'w') as f:
    f.writelines(new_lines)

# Verify
with open(path, 'r') as f:
    for i, line in enumerate(f, 1):
        if 'OKX' in line or 'TRADE' in line:
            print(f'{i}: {line.rstrip()}')
