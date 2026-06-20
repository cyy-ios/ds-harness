import re

def to_snake_case(name):
    # 转换为 snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    s2 = re.sub(r'[^a-z0-9]+', '_', s2).strip('_')
    return s2
