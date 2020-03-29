from os import path
import chardet
import pandas as pd
import re

DIR_PATH = path.dirname(path.realpath(__file__))


def process_subtitles_by_line(fpath, encoding):
    subtitle_dict = {
        'subtitle_index': [],
        'start': [],
        'end': [],
        'text': []
    }
    with open(fpath, 'r', encoding=encoding) as f:
        text_accumulator = []  # gathers multi-line subtitles
        for line in f:
            index_match = re.match(r'([0-9]+)\n', line)
            newline_match = re.fullmatch(r'\n', line)

            if index_match:
                # line is subtitle index
                index_int = int(index_match.group(1))
                subtitle_dict['subtitle_index'].append(index_int)
            elif re.search(r'-->', line):
                try:
                    start, end = re.findall(r'([0-9]{2}:[0-9]{2}:[0-9]{1,2},[0-9]{2,3})', line)
                except ValueError:
                    print(line)
                # subtitle_dict['start'].append(strptime(start, '%H:%M:%S,%f'))
                # subtitle_dict['end'].append(strptime(end, '%H:%M:%S,%f'))
                subtitle_dict['start'].append(start)
                subtitle_dict['end'].append(end)
            elif newline_match:
                # blank line between subtitles
                full_subtitle = ' '.join(text_accumulator)
                subtitle_dict['text'].append(full_subtitle)
                text_accumulator = []  # reset accumulator
            else:
                # text of the dialogue
                text_accumulator.append(line.strip())
        # Save the text contents of the last loop
        full_subtitle = ' '.join(text_accumulator)
        subtitle_dict['text'].append(full_subtitle)
    return subtitle_dict


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
            'episode_name': m.group(3)
        }
    else:
        raise ValueError()
    return ep_dict


def add_episode_data(df, ep_dict):
    for col, val in ep_dict.items():
        df[col] = val
    return df


def main():
    filename = 'Westworld - 2x01 - Journey Into Night.WEB.DEFLATE.en.srt'
    fpath = path.join(DIR_PATH, '..', 'subtitles', filename)
    # Detect proper encoding
    with open(fpath, 'rb') as rawdata:
        result = chardet.detect(rawdata.read(100000))
        # For S02E01, it's ISO-8859-1

    # Parse episode name and number
    episode_dict = parse_episode_filename(path.basename(fpath))

    sub_dict = process_subtitles_by_line(fpath, result['encoding'])
    df_data = pd.DataFrame.from_dict(sub_dict)
    df_data = convert_time_cols(df_data)
    df_data = drop_bad_rows(df_data)
    df_data = add_episode_data(df_data, episode_dict)
    print(df_data.head())

    # Write out
    outname = 'S{season_num}E{episode_num:02}_subtitles.csv'.format(**episode_dict)
    outpath = path.join(DIR_PATH, '..', 'data', outname)
    df_data.to_csv(outpath, index=False, encoding='utf-8')
    print(f'Subtitle data written to {outpath}')


if __name__ == '__main__':
    main()
