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
    """Some subtitles are just font and website info"""
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
    return df_data


def main():
    df_all = pd.DataFrame()
    subtitle_path = path.join(DIR_PATH, '..', 'subtitles', '*.srt')
    for filepath in glob(subtitle_path):
        print(filepath)
        #fpath = path.join(DIR_PATH, '..', 'subtitles', filename)
        df_episode = all_file_actions(filepath)
        df_all = df_all.append(df_episode)

    # Write out
    outname = 'subtitle_data.csv'
    outpath = path.join(DIR_PATH, '..', 'data', outname)
    df_all.to_csv(outpath, index=False, encoding='utf-8')
    print(f'Subtitle data written to {outpath}')


if __name__ == '__main__':
    main()
