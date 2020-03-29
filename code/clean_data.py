from os import path
import pandas as pd
import re

DIR_PATH = path.dirname(path.realpath(__file__))

# Compile regex for cleaning
HTML_REMOVE_R = re.compile('<.*?>')
HTML_REFTAG = re.compile(r'<ref.*</ref>')


def drop_unused_columns(df):
    """ Drop specific and under-used columns

    image, images, imagecaption: just filenames of images in the wiki
    appearedin: infrequently used episode count or list of episode names
    """
    # Drop specific columns
    drop_cols = ['image', 'images', 'imagecaption', 'appearedin']
    df = df.drop(columns=drop_cols)

    # Drop mostly empty columns (less than 15 non-null values)
    df = df.dropna(axis=1, how='any', thresh=15)
    return df


def remove_html(s):
    """Converts some html tags to unicode, then discards the rest."""
    s = re.sub(r'<br/>', '\n', s)
    s = re.sub(HTML_REFTAG, '', s)
    s =  re.sub(HTML_REMOVE_R, '', s)
    return s


def remove_markdown(s):
    """Remove double brackets and bullets for wiki markdown"""
    s = re.sub(r'\[{2}|\]{2}', '', s)
    s = re.sub(r'\*', '', s)
    return s


def fix_species(df):
    """Map certain abnormal values of species."""
    species_map = {
        'Human & Host': 'Both',
        'Unknown': None,
        'Host/Simulated': 'Simulation',
        'Human/Simulation': 'Simulation',
    }
    df['species'] = df['species'].replace(species_map)


def update_host_human(df):
    """Fill NAs in species based on host/human bools (from wiki categories)."""
    missing_host = (df.is_host) & (df.species.isna())
    missing_human = (df.is_human) & (df.species.isna())
    df['species'] = df['species'].mask(missing_host, 'Host')
    df['species'] = df['species'].mask(missing_human, 'Human')
    return df


def main():
    chars_raw_path = path.join(DIR_PATH, '..', 'data', 'characters.csv')
    chars_raw = pd.read_csv(chars_raw_path, encoding='utf-8')

    # Work with a new copy
    chars = chars_raw.copy()
    chars = drop_unused_columns(chars)

    # Clean all string columns
    for col in chars.select_dtypes(include='object'):
        chars[col] = (chars[col]
                      .map(remove_html, na_action='ignore')
                      .map(remove_markdown, na_action='ignore')
                      )
        # Replace every TBA with null
        chars[col] = chars[col].replace(to_replace='TBA', value=None)

    # Gender to title case
    chars['gender'] = chars['gender'].str.title()

    # Drop movie characters
    chars = chars.drop(index=chars[chars.name.str.contains(r'\(19[0-9]{2}\)')].index)

    # Drop categories
    chars = chars.drop(index=chars[chars.url.str.contains('Category')].index)

    fix_species(chars)
    chars = update_host_human(chars)

    # Write out
    outfile = path.join(DIR_PATH, '..', 'data', 'characters_clean.csv')
    chars.to_csv(outfile, index=False, encoding='utf-8')
    print(f'Characters (clean) written to {outfile}')


if __name__ == '__main__':
    main()