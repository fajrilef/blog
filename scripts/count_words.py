import re
content = open('src/content/blog/tech/cara-mengecek-kesehatan-baterai-laptop.mdx').read()
body = content.split('---', 2)[2]
body = re.sub(r'```.*?```', ' ', body, flags=re.S)
body = re.sub(r'[#*_\[\]()>|`-]', ' ', body)
words = re.findall(r'\S+', body)
print('Kata (perkiraan):', len(words))
