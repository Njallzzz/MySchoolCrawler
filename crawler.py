import requests
from bs4 import BeautifulSoup as bs4
import os
import getpass
import subprocess
import urllib.parse as urlparse

username = input('MySchool Username: ')
password = getpass.getpass('MySchool Password: ');

myschool_base_url = 'https://myschool.ru.is/myschool'
session = requests.Session()

res = session.get(myschool_base_url, auth=(username, password))

if res.status_code != 200:
    print('Unable to login, MySchool returned:', res.status_code)
    exit(1)

soup = bs4(res.text, 'html.parser')
res = [ x['href'] for x in soup.find('td', {'class': 'ruLeft'}).findAll('a') if 'Námskeið' in x.getText() ]
if len(res) > 1 or len(res) < 1:
    print('Internal error 1')
    exit(1)

myschool_extended_url = myschool_base_url + '/' + res[0]
res = session.get(myschool_extended_url, auth=(username, password))
if res.status_code != 200:
    print('Unable to retrieve schedule, MySchool returned:', str(res.status_code))
    exit(1)

soup = bs4(res.text, 'html.parser')
to_retrieve = [ (x.find('span')['title'].splitlines()[1].split(',')[1].split('.')[0], x.find('a')['href']) for x in soup.find('div', {'class': 'ruTabs'}).findAll('li') ]

print('Preparing to retrieve: ', end='')
for item in to_retrieve:
    print(item[0]+ ' ', end='')
print()

for item in to_retrieve:
    try:
        os.makedirs(item[0])
    except FileExistsError:
        pass
    myschool_extended_url = myschool_base_url + '/' + item[1]
    res = session.get(myschool_extended_url, auth=(username, password))
    if res.status_code != 200:
        print('Unable to retrieve: ' + item[0] + ', MySchool returned: ' + str(res.status_code))
        continue

    soup = bs4(res.text, 'html.parser')
    res = [ [y.getText(), y['href']] for y in [x for x in soup.find('td', {'class': 'ruRight'}).findAll('table')
                                                if x.find('a', {'class': 'mainMenu'}).getText() == 'Kennsluefni' ][0].findAll('a', {'class': 'subMenu'})
             if 'Prenta síðu' not in y.getText()]
    for category in res:
        if category[0] not in 'Fyrirlestrar' and category[0] not in 'Annað efni':
            continue
        print(item, category)
        
        myschool_extended_url = myschool_base_url + '/' + category[1]
        res = session.get(myschool_extended_url, auth=(username, password))
        if res.status_code != 200:
            print('Unable to retrieve: ' + item[0] + ', MySchool returned: ' + str(res.status_code))
            continue
        soup = bs4(res.text, 'html.parser')

        collection = {}
        if 'Fyrirlestrar' in category[0]:
            row1 = soup.findAll('tr', {'class': 'ruTableRow1'})
            row2 = soup.findAll('tr', {'class': 'ruTableRow2'})
            all_rows = row1 + row2            
            for elem in all_rows:
                entry = {}
                entry['youtube'] = []
                entry['download'] = []
                for col in elem.select('td > a'):
                    if col.has_attr('href') and 'youtu' in col['href']:
                        entry['youtube'].append(col['href'])
                    elif col.has_attr('href') and not col['href'].startswith('http'):
                        entry['download'].append(myschool_base_url + '/' + col['href'])
                try:
                    title = elem.find("td", {'align':'left', 'title':''}).get_text()
                    title = title.replace(':', '').replace('"', '').replace('\\', '').replace('/', '').strip()
                    collection[title] = entry
                except:
                    pass

        for down in collection.items():
            print('Downloading:', down[0].strip())
            path = os.path.join(item[0], down[0].strip())
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for normdownload in down[1]['download']:
                parsed = urlparse.urlparse(normdownload)
                print('File:', urlparse.parse_qs(parsed.query)['File'][0])
                res = session.get(normdownload, stream=True, auth=(username, password))
                if res.status_code != 200:
                    print('Unable to retrieve item: ' + item[0] + ', MySchool returned: ' + str(res.status_code))
                    continue
                with open(os.path.join(path, urlparse.parse_qs(parsed.query)['File'][0]), 'wb') as f:
                    for chunk in res.iter_content(chunk_size=1024): 
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
            for normdownload in down[1]['youtube']:
                print('Youtube:', normdownload)
                process = subprocess.Popen(['youtube-dl', normdownload], cwd=path, shell=True)
                out, err = process.communicate()
            

