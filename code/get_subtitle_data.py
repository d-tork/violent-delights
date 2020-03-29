"""Creates structured data from subtitle files.

# TODO:
[x] mark any line with <i> tags as a character being off-screen
[x] look for lines that begin with "[name]:" as it may also be
    an off-screen character, but the name will make for great attribution
[ ] fuzzy string matching to find character names mentioned in dialogue
"""
from glob import glob
from os import path
import chardet
import pandas as pd
import re

DIR_PATH = path.dirname(path.realpath(__file__))


def process_subtitles_by_line(fhand, sub_dict):
    """Adds lines to proper dictionary key.

    Updates in place, returns nothing.
    """
    text_accumulator = []  # gathers multi-line subtitles
    for line in fhand:
        index_match = re.match(r'([0-9]+)\n', line)
        newline_match = re.fullmatch(r'\n', line)

        if index_match:
            # line is subtitle index
            index_int = int(index_match.group(1))
            sub_dict['subtitle_index'].append(index_int)
        elif re.search(r'-->', line):
            try:
                start, end = re.findall(r'([0-9]{2}:[0-9]{2}:[0-9]{1,2},[0-9]{2,3})', line)
            except ValueError:
                print(line)
            # subtitle_dict['start'].append(strptime(start, '%H:%M:%S,%f'))
            # subtitle_dict['end'].append(strptime(end, '%H:%M:%S,%f'))
            sub_dict['start'].append(start)
            sub_dict['end'].append(end)
        elif newline_match:
            # blank line between subtitles
            if not text_accumulator:
                # no text has been gathered since last iteration, skip the store
                continue
            full_subtitle = ' '.join(text_accumulator)
            sub_dict['text'].append(full_subtitle)
            text_accumulator = []  # reset accumulator
        else:
            # text of the dialogue
            text_accumulator.append(line.strip())
    # Save the text contents of the last loop
    full_subtitle = ' '.join(text_accumulator)
    sub_dict['text'].append(full_subtitle)


def convert_time_cols(df):
    for col in ['start', 'end']:
        df[col] = pd.to_datetime(df[col], format='%H:%M:%S,%f').dt.time
    return df


def drop_bad_rows(df):
    """Some subtitles are just font and website info.

    This occurs before html tags are cleaned.
    """
    # Drop font color rows
    df = df.drop(index=df.loc[df.text.str.contains('<font')].index)
    return df


def parse_episode_filename(fname):
    """Gets episode number and name from file."""
    pat = r'Westworld - ([1-3])x([0-9]{1,2}) - ([^\.]+)\..+.srt'
    m = re.match(pat, fname)
    if m:
        ep_dict = {
            'season_num': int(m.group(1)),
            'episode_num': int(m.group(2)),
            'episode_name': m.group(3),
            'filename': fname
        }
    else:
        raise ValueError()
    return ep_dict


def add_episode_data(df, ep_dict):
    for col, val in ep_dict.items():
        df[col] = val
    return df


def detect_file_encoding(fpath):
    """For S02E01, it's ISO-8859-1"""
    with open(fpath, 'rb') as rawdata:
        result = chardet.detect(rawdata.read(100000))
    return result['encoding']


def mark_offscreen_dialogue(df):
    """Flags if line was delivered by someone off-screen.

    Depends on html <i> tags, so do this before cleaning.
    """
    df['offscreen'] = df['text'].str.contains('<i>')


def explode_multicharacter_subtitle(df):
    """Explode data when single subtitle covers multiple people.

    Detectable with a hyphen followed by a space.
    """
    df['textsplit'] = df['text'].str.split(pat='- ')
    # Remove empty strings from textsplit lists
    df['textsplit'] = df['textsplit'].apply(
        lambda l: [x for x in l if len(x) > 0]
    )
    df = df.explode('textsplit')
    # Rename columns for precision
    df = df.rename(columns={
        'text': 'fulltext',
        'textsplit': 'text'
    })
    return df


def remove_html_tags(df, colname):
    """Remove all html from a series."""
    df[colname] = df[colname].str.replace('<[^<]+?>', '')
    return df


def get_attributable_speaker(df):
    """If a speaker is attributable, extract their name."""
    speaker_pat = r'(.+):.*'
    df['speaker'] = df['text'].str.extract(speaker_pat)
    df['speaker'] = df['speaker'].str.upper()

    # Drop any "speakers" whose name is longer than 3 words (i.e.
    # just a colon being used in the dialogue)
    # This keeps 'Guy #2' and 'Man in Black', but not 'The real question is'
    df['_spkr_word_count'] = df['speaker'].fillna('').str.split().map(len)
    df['_attributable'] = (
            (df['_spkr_word_count'] > 0) &
            (df['_spkr_word_count'] <= 3)
    )
    # Fill with null the speakers made of more than 3 words
    df['speaker'] = df['speaker'].where(df['_attributable'])
    # Clean up temp columns
    df = df.drop(columns=['_spkr_word_count', '_attributable'])
    return df


def drop_empty_rows(df):
    """Where text ended up an empty string w/ spaces.

    So far, this was just S01E01 - The Original."""
    return df.drop(index=df.loc[df.text == ' '].index)


def all_file_actions(fpath):
    """Creates dataframe for single episode."""
    # Parse episode name and number
    episode_dict = parse_episode_filename(path.basename(fpath))

    subtitle_dict = {
        'subtitle_index': [],
        'start': [],
        'end': [],
        'text': []
    }

    encoding_guess = detect_file_encoding(fpath)
    with open(fpath, 'r', encoding=encoding_guess) as f:
        process_subtitles_by_line(f, subtitle_dict)
    df_data = pd.DataFrame.from_dict(subtitle_dict)
    df_data = convert_time_cols(df_data)
    df_data = drop_bad_rows(df_data)
    df_data = add_episode_data(df_data, episode_dict)
    df_data = explode_multicharacter_subtitle(df_data)
    mark_offscreen_dialogue(df_data)
    df_data = remove_html_tags(df_data, 'text')
    df_data = get_attributable_speaker(df_data)
    df_data = drop_empty_rows(df_data)
    return df_data


def main():
    df_all = pd.DataFrame()
    subtitle_path = path.join(DIR_PATH, '..', 'subtitles', '*.srt')
    for filepath in glob(subtitle_path):
        print(filepath)
        df_episode = all_file_actions(filepath)
        df_all = df_all.append(df_episode)

    # Write out
    outname = 'subtitle_data.csv'
    outpath = path.join(DIR_PATH, '..', 'data', outname)
    df_all.to_csv(outpath, index=False, encoding='utf-8')
    print(f'Subtitle data written to {outpath}')


if __name__ == '__main__':
    main()
