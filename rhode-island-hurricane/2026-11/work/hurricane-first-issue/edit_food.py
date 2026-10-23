import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'research/food/food-stories.json'
articles = json.loads(path.read_text())

scialo, venda, matunuck, iggys = articles

scialo['body'][2] = {
    'text': 'The job came with a change of status, from owner to employee, but Gaeta sounded pleased to be back. “Retirement is no fun!” she told WJAR in 2021.',
    'sources': [1]
}
scialo['body'][3] = {
    'text': 'The current menu at 257 Atwells Avenue includes ricotta pie, blackberry crostata, wine biscuits and cannoli. The fall selection adds an apricot-and-almond-paste tart. Somebody still has to settle the argument over what to bring to dinner.',
    'sources': [2]
}
scialo['body'][5] = {
    'text': 'In 2026, the Scialo name is 110 years old. The bakery has changed hands and survived a closure. There are still cannoli on Atwells Avenue bearing that name.',
    'sources': [2, 3]
}
scialo['source_notes'][0]['claims'].append('Gaeta’s four-word retirement remark is explicitly dated to her 2021 interview.')
scialo['reporting_limits'] = [x.replace('or direct quotations', '') for x in scialo['reporting_limits']]
scialo['reporting_limits'].append('The single four-word quotation comes from WJAR’s 2021 interview and is attributed and dated in the copy.')

venda['title'] = 'Sunday Starts at Venda'
venda['dek'] = 'Ravioli, pumpkin tortelloni and the Costantino family’s long life on Federal Hill.'
venda['body'][0] = {
    'text': 'Somebody has to make the ravioli. At Venda, that job has supported a Federal Hill business for generations and given the rest of us a head start on Sunday dinner.',
    'sources': [1]
}
venda['body'][2] = {
    'text': 'The current pickup menu includes five-cheese and spinach ravioli, plus prosciutto-and-provolone ravioli. For an autumn dinner, there is pumpkin tortelloni. Picking a filling may turn out to be the difficult part.',
    'sources': [2]
}
venda['body'][3] = {
    'text': '“It all starts with the ingredients,” Costantino told Food Finessa in 2022. He pointed to flour and cheeses, including ricotta and pecorino paglierino. The interview returned a growing business to the contents of the pasta itself.',
    'sources': [3]
}
venda['body'][5] = {
    'text': 'The company’s catalog stretches well past ravioli, through manicotti, stuffed shells, tortellini and angel hair. That is plenty of room to change dinner without giving up the Sunday ritual.',
    'sources': [1]
}
venda['source_notes'][2]['claims'].append('Six-word quotation about ingredients, plus the cheeses identified in that same published interview.')
venda['reporting_limits'] = [x.replace('No recipe, cooking directions or direct quotation reproduced.', 'No recipe or cooking directions reproduced. One six-word quotation is attributed to the published 2022 interview.') for x in venda['reporting_limits']]

matunuck['title'] = 'The Farmer Behind Matunuck Oyster Bar'
matunuck['dek'] = 'Perry Raso needed a dock for his oyster boats. The restaurant came next. Then a fire tested everything he had built.'
matunuck['body'][2] = {
    'text': 'The restaurant followed a practical need. Raso wanted commercial dock access for his oyster boats. He bought the waterside property and opened the restaurant in 2009. The boats needed a place to land; the restaurant gave the farm another way to reach customers.',
    'sources': [1]
}
matunuck['body'][4] = {
    'text': 'The farm’s published tour description traces aquaculture and shellfish through different stages of growth. Matunuck’s own oysters are raised in Potter Pond. That connection between a specific pond and the plate was there before the fire, before the tent and before the restaurant became the best-known part of Raso’s work.',
    'sources': [3]
}
matunuck['body'][5] = {
    'text': 'Raso told Donnis that he initially resisted a suggestion to put a tent across the street, worrying it would damage the business’s reputation. He changed his mind. “It really saved us,” he said.',
    'sources': [2]
}
matunuck['source_notes'][1]['claims'].append('Raso’s initial objection to the temporary tent, his changed view, and the four-word quotation that it saved the business.')
matunuck['reporting_limits'] = [x.replace('or direct quotations', '') for x in matunuck['reporting_limits']]
matunuck['reporting_limits'].append('One four-word quotation comes from the July 2026 Ocean State Media interview. The original dining room’s reopening remains an unresolved publication update.')

iggys['dek'] = 'How a father’s nickname and a son’s promise became a Rhode Island clam-shack fixture.'
iggys['body'][2] = {
    'text': 'Rhode Island Monthly traced the early chowder specialty to Sally’s side of the family: Manhattan red. A restaurant now known for offering choices started with a particular family recipe.',
    'sources': [2]
}
iggys['body'][4] = {
    'text': 'The original Warwick location operates year-round, according to its official page. The clam cakes do not disappear with the beach towels. Neither does the argument over which chowder belongs beside them.',
    'sources': [3]
}
iggys['body'][5] = {
    'text': 'The family’s history records a more serious promise behind the business. Before Gaetano died, he asked David to carry it on. David was a senior at Johnson & Wales, with choices ahead of him. He kept the promise.',
    'sources': [1]
}
iggys['source_notes'][0]['claims'].append('David was a Johnson & Wales senior when his father asked him to carry on the business.')

for article in articles:
    article['section'] = article['category']
    article['bodyparagraphs'] = [p['text'] for p in article['body']]
    article['word_count'] = sum(len(p['text'].split()) for p in article['body'])
    for source in article['source_notes']:
        if not source.get('date'):
            source['date'] = 'Accessed October 23, 2026'

path.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
print([(a['title'], a['word_count']) for a in articles])

culture_path = root / 'research/culture/florence.json'
culture = json.loads(culture_path.read_text())
culture['body'][3]['text'] = culture['body'][3]['text'].replace('Rhode Island’s connection began long before the musicians booked their flights. ', '')
culture_path.write_text(json.dumps(culture, ensure_ascii=False, indent=2))
