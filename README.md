# Violent Delights

Inspired by [Data Wrangling Westworld](https://mode.com/blog/data-mining-westworld)
by Joel Carron.

Carron's original project built a dataset from episode scripts from 
springfieldspringfield.co.uk (which is now shut down). Additionally, the scripts
were missing character names, so they needed to re-watch each episode and add
the names manually.

Since this project is more about relationships than an analysis of the dialogue,
I won't need to go that far. 

## Data collection

### Wiki
Initial data is coming from the [Westworld Wiki](https://westworld.fandom.com/).
It is either fetched through the [API](https://westworld.fandom.com/api/v1/) or
scraped from the [XML export](https://en.wikipedia.org/wiki/Help:Export) when
the API is insufficient.

### Scripts/Subtitles
Since no good source for all episode scripts is available, I may resort to
analyzing subtitle files for character name mentions within a certain number
of minutes, which may indicate that characters are talking to or about one
another.

Subtitle files downloaded from http://www.tvsubtitles.net/tvshow-2081-3.html
