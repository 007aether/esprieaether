path = '/c/Users/ESPRIEAETHER/Desktop/esprieaether/.env'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('OKX_API_KEY='):
        new_lines.append('OKX_API_KEY=c9aca4f1-5974-4a22-997e-7bd1b2beafc5\n')
    elif line.startswith('OKX_SECRET_KEY='):
        new_lines.append('OKX_SECRET_KEY=275DF7BAF63F4B05CCC02AFCCC696BF6\n')
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
