import re
text = open('src/content/blog/living/berapa-lama-sayuran-bisa-disimpan-di-kulkas.mdx').read()
body = re.sub(r'^---.*?---', '', text, flags=re.DOTALL)
body = re.sub(r'[#*_>`\-]', ' ', body)
words = body.split()
print('total kata (whitespace):', len(words))
