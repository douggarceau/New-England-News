"""Tag each directory item with a neighborhood (field 'h'). Run after editing data/directory.json."""
import json,re,collections
P='data/directory.json'
NAMES=[('Esplanade','Back Bay'),('Leather District','Downtown & Theater District'),('860A Beacon','Fenway & Kenmore'),('South End','South End'),('Back Bay','Back Bay'),('Copley','Back Bay'),('Newbury','Back Bay'),('Beacon Hill','Beacon Hill & West End'),('West End','Beacon Hill & West End'),('North End','North End'),('Seaport','Seaport & Waterfront'),('waterfront','Seaport & Waterfront'),('Fort Point','Seaport & Waterfront'),('Fenway','Fenway & Kenmore'),('Kenmore','Fenway & Kenmore'),('Theater District','Downtown & Theater District'),('Theatre District','Downtown & Theater District'),('Chinatown','Downtown & Theater District'),('Downtown','Downtown & Theater District'),('Faneuil','Downtown & Theater District'),('Financial District','Downtown & Theater District'),('Bay Village','South End'),('Jamaica Plain','Jamaica Plain'),('Dorchester','Dorchester'),('South Boston','South Boston'),('Charlestown','Charlestown'),('East Boston','East Boston'),('Allston','Allston & Brighton'),('Brighton','Allston & Brighton'),('Roxbury','Roxbury'),('Roslindale','Roslindale & Mattapan'),('Mattapan','Roslindale & Mattapan'),('Cambridge','Cambridge'),('Somerville','Somerville'),('Brookline','Greater Boston')]
Z={'02116':'Back Bay','02199':'Back Bay','02117':'Back Bay','02118':'South End','02108':'Beacon Hill & West End','02114':'Beacon Hill & West End','02113':'North End','02109':'Downtown & Theater District','02110':'Downtown & Theater District','02111':'Downtown & Theater District','02210':'Seaport & Waterfront','02115':'Fenway & Kenmore','02215':'Fenway & Kenmore','02129':'Charlestown','02122':'Dorchester','02124':'Dorchester','02125':'Dorchester','02121':'Dorchester','02130':'Jamaica Plain','02128':'East Boston','02127':'South Boston','02134':'Allston & Brighton','02135':'Allston & Brighton','02119':'Roxbury','02120':'Roxbury','02131':'Roslindale & Mattapan','02126':'Roslindale & Mattapan','02138':'Cambridge','02139':'Cambridge','02140':'Cambridge','02141':'Cambridge','02142':'Cambridge','02143':'Somerville','02144':'Somerville','02145':'Somerville'}
ST=[(r'newbury|boylston|commonwealth ave(?!.*(bu|university))|dartmouth|exeter st|huntington ave|prudential|copley','Back Bay'),(r'harrison ave|shawmut|columbus ave|union park|sowa|ink block','South End'),(r'hanover st|salem st|north st','North End'),(r'charles st|cambridge st|causeway|td garden','Beacon Hill & West End'),(r'lansdowne|brookline ave|jersey st|ipswich','Fenway & Kenmore'),(r'seaport|northern ave|congress st|summer st|fan pier|harbor','Seaport & Waterfront'),(r'washington st|tremont st|state st|court st|winter st|union st|school st|milk st|stuart st','Downtown & Theater District')]
CITY='Boston'
def tag(a):
    m=re.search(r'\b(02\d{3})\b',a)
    for k,v in NAMES:
        if k.lower() in a.lower(): return v
    if m and m.group(1) in Z: return Z[m.group(1)]
    al=a.lower()
    if re.search(r'\bboston\b|^\s*$|\bma\b',al) or ',' not in a:
        for r,v in ST:
            if re.search(r,al): return v
        return 'Citywide'
    return 'Greater Boston'
d=json.load(open(P))
for x in d['items']: x['h']=tag(x.get('a',''))
order=['Back Bay','South End','Beacon Hill & West End','Downtown & Theater District','North End','Seaport & Waterfront','Fenway & Kenmore','Charlestown','South Boston','Dorchester','Jamaica Plain','Roxbury','Roslindale & Mattapan','East Boston','Allston & Brighton','Cambridge','Somerville','Greater Boston','Citywide']
d['hoods']=[h for h in order if any(x['h']==h for x in d['items'])]
json.dump(d,open(P,'w'),ensure_ascii=False,indent=1)
print(collections.Counter(x['h'] for x in d['items']).most_common())
