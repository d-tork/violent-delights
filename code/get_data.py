from os import path
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re

DIR_PATH = path.dirname(path.realpath(__file__))


def get_links(char_dict):
    page_sections = requests.get(f"https://westworld.fandom.com/api/v1/Articles/AsSimpleJson?id={char_dict['id']}").json()['sections']

    # Get Relationships sections
    try:
        rel_section = [x for x in page_sections if x['title'] == 'Relationships'][0]
        rel_section_start = page_sections.index(rel_section) + 1
        rel_next_section = [x for x in page_sections[rel_section_start:] if x['level'] == 2][0]
        rel_section_end = page_sections.index(rel_next_section)
    except IndexError:  # no relationships, forever alone
        return None

    links = [sec['title'] for sec in page_sections[rel_section_start:rel_section_end]]
    if links:
        return links
    else:  # sometimes the Relationships section exists, but it's empty
        return None


def add_species_label(char_dict):
    """Add is_host and is_human keys to character dictionary."""
    # Get names from wiki category
    hosts_request = \
        requests.get('https://westworld.fandom.com/api/v1/Articles/List?expand=1&category=Hosts&limit=200').json()['items']
    humans_request = \
        requests.get('https://westworld.fandom.com/api/v1/Articles/List?expand=1&category=Human&limit=200').json()['items']
    hosts = [x['id'] for x in hosts_request]
    humans = [x['id'] for x in humans_request]

    for char in char_dict:
        char['is_host'] = char['id'] in hosts
        char['is_human'] = char['id'] in humans


def construct_xml_url(char_dict):
    """Get the URL for the XML export of a wiki page."""
    base_url = 'https://westworld.fandom.com'
    url_str = char_dict['url'].split('/')
    url_str.insert(2, 'Special:Export')
    url_str = '/'.join(url_str)
    url_str = base_url + url_str
    return url_str


def get_pagetext(resp):
    """Get full text of wiki page from XML response.

    To preview the tree and how I arrived at these lists:
    ```
    for child in root:
        print(child.tag)
    page = root[1]
    for i, subpage in enumerate(page):
        print('\t', i, subpage.tag)
        for j, thing in enumerate(subpage):
            print('\t\t', j, thing.tag)
    ```

    Args:
        resp: response from XML request

    Returns: string
    """
    root = ET.ElementTree(ET.fromstring(resp.text)).getroot()
    page = root[1]
    revision = [x for x in page if 'revision' in x.tag][0]
    pagetext = [x for x in revision if 'text' in x.tag][0].text
    return pagetext


def get_infobox(pt):
    """Get and organize the infobox stats from a page.

    Args:
        pt (str): page text in wikipedia markdown format

    Returns: dict
    """
    info_start = pt.find('|')
    info_end = pt.find('}}', info_start + 50)  # skip ahead, in case {{PAGENAME}} follows
    info = pt[info_start:info_end]
    info_list = info.split('|')

    info_dict = {}
    pat = r'(\w+)\s*=\s{1}([\s\S]*)'
    for line in info_list:
        match = re.fullmatch(pat, line.strip())
        if match:
            info_dict[match.group(1)] = match.group(2)
    return info_dict


def scrape_all_features(char_list):
    for char in char_list:
        scrape_url = construct_xml_url(char)
        scrape_resp = requests.get(scrape_url)
        scrape_pt = get_pagetext(scrape_resp)
        try:
            scrape_ib = get_infobox(scrape_pt)
            # TODO: scrape pagetext for categories as well
            # TODO: scrape pagetext for character name mentions
        except Exception as e:
            print(f"Failed to scrape {char['name']}! ({e})")
            continue
        char.update(scrape_ib)


def main():
    # Get node names and ids
    chars_request = requests.get('https://westworld.fandom.com/api/v1/Articles/List?expand=1&category=Characters&limit=200').json()['items']
    chars = [dict(id=x['id'], name=x['title'], url=x['url']) for x in chars_request]

    loc_request = requests.get('https://westworld.fandom.com/api/v1/Articles/List?expand=1&category=Locations&limit=200').json()['items']
    locs = [dict(id=x['id'], name=x['title'], url=x['url']) for x in loc_request]

    tech_request = requests.get('https://westworld.fandom.com/api/v1/Articles/List?expand=1&category=Technology&limit=200').json()['items']
    tech = [dict(id=x['id'], name=x['title'], url=x['url']) for x in tech_request]

    park_request = requests.get('https://westworld.fandom.com/api/v1/Articles/List?expand=1&category=Park management&limit=200').json()['items']
    parks = [dict(id=x['id'], name=x['title'], url=x['url']) for x in park_request]

    # Collect relationships
    print('Finding links...')
    for character in chars:
        character['links'] = get_links(character)
    print('\t done.\n')

    add_species_label(chars)
    print('Getting attributes...')
    scrape_all_features(chars)
    print('\t done.\n')

    # Write out
    df_chars = pd.DataFrame.from_dict(chars).set_index('id')
    outfile = path.join(DIR_PATH, '..', 'data', 'characters.csv')
    df_chars.to_csv(outfile)
    print(f'Characters written to {outfile}')


if __name__ == '__main__':
    main()