import ast

with open('kiosk.py', 'r') as f:
    tree = ast.parse(f.read())

for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == 'LongPressButton':
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        print(f"LongPressButton methods ({len(methods)}):", methods)
