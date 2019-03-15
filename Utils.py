import base64
import json
import os
import re
import urllib.parse
from colorsys import hls_to_rgb
from defs import PFIVE, GFIVE, FBS
from datetime import datetime

from subprocess import Popen

import requests
from bs4 import BeautifulSoup as bs
from scipy.stats import norm


class Utils:
    headers = {'User-Agent': 'Mozilla/5.0'}

    @staticmethod
    def calculate_win_prob_from_spplus(a, b, loc):
        if loc == 'home':
            return norm.cdf((a - b + 2.5) / 17)
        elif loc == 'neutral':
            return norm.cdf((a - b) / 17)
        else:
            return norm.cdf((a - b - 2.5) / 17)

    @staticmethod
    def download_logos(width=40, height=40):
        # Quick and dirty method to scrape logos from ESPN; they need minor editorial cleanup afterward
        r = requests.get('http://www.espn.com/college-football/teams')
        results = bs(r.text).findAll('a', href=re.compile('^/college-football/team/_/id/'))
        if not os.path.exists('./Resources/'):
            os.makedirs('./Resources/')

        for link in results:
            foo = link['href'].split('/')
            id = foo[5]
            name = foo[6].split('-')[0].title()
            pic_url = 'http://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/{}.png&h={}&w={}'.format(id,
                                                                                                          height,
                                                                                                          width)
            with open(os.path.join('./Resources/', '{}.png'.format(name.lower())), 'wb') as handle:
                response = requests.get(pic_url, stream=True)

                if not response.ok:
                    print(response)

                for block in response.iter_content(1024):
                    if not block:
                        break

                    handle.write(block)


    @staticmethod
    def get_color_brightness(red, green, blue):
        """Return (float) representing the color brightness as calculated using the standard W3C formula."""
        return (red * 299 + green * 587 + blue * 114) / 1000

    @staticmethod
    def get_text_contrast_color(red, green, blue):
        # Should the text be white or black?
        if Utils.get_color_brightness(red, green, blue) > 123:
            return 0, 0, 0
        else:
            return 255, 255, 255

    @staticmethod
    def gradient_color(lower, upper, val, method='linear', scale='red-green', primaryColor=None,
                       secondaryColor=None):
        """ Return (red, green, blue) interpolated along the color scale specified."""
        # Perform linear interpolation on the hue between 0.33 and 0, then convert back to RGB
        # HLS 0.33, 0.65, 1.0 will give green
        # HLS 0, 0.65, 1.0 will give red
        inter = Utils.interpolate(lower, upper, val, method=method)

        if scale == 'team':
            if not (primaryColor and secondaryColor):
                pass
            else:
                # brighter colors should mean higher probabilities, as a general rule
                # convert the hex values to rgb then order the colors by brightness
                colors = sorted([x for x in [primaryColor, secondaryColor]],
                                key=lambda y: Utils.get_color_brightness(*y))
                return [colors[0][i] + inter * (colors[1][i] - colors[0][i]) for i in (0, 1, 2)]

        if scale == 'red-green':
            if upper == lower:
                h = 120
            else:
                h = 120 * inter

            return [int(round(255 * x, 0)) for x in hls_to_rgb(h / 360.0, 0.65, 1)]

        if scale == 'red-blue':
            # interpolate 0-0.5 as red-white, 0.5-1 as white-blue
            if inter > 0.5:
                return [int(round(255 * x, 0)) for x in hls_to_rgb(0.66, 1.5 - inter, 0.4)]
            else:
                return [int(round(255 * x, 0)) for x in hls_to_rgb(0, 0.5 + inter, 0.75)]

        if scale == 'black-red':
            return [int(round(255 * x, 0)) for x in hls_to_rgb(0, 0.5 * inter, 1)]

    @staticmethod
    def hex_to_rgb(value):
        """Return (red, green, blue) for the color given as #rrggbb."""
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    @staticmethod
    def interpolate(lower, upper, val, method='linear'):
        if upper == lower:
            return 1
        elif method.lower() == 'cubic':
            x = (val - lower) / (upper - lower)
            return x ** 3 * (10 + x * (-15 + 6 * x))
        else:
            return (val - lower) / (upper - lower)

    @staticmethod
    def scrape_png_links(format='reddit'):
        with open("schedule.json", "r") as file:
            schedule = json.load(file)

        scale = ['red-green']
        result = {}
        out = ''
        for j in scale:
            url = 'https://github.com/EvRoHa/SP-plus-Visualizations/tree/master/png output/sp+ - {}/'.format(j)
            r = requests.get(url, headers=Utils.headers)

            search_url = urllib.parse.quote(
                '/EvRoHa/SP-plus-Visualizations/blob/master/png output/sp+ - {}/'.format(j))
            links = bs(r.text).findAll('a', href=re.compile(search_url + '*'))

            for x in links:
                name = x.text.split('~')[0].strip().title()
                url = re.sub('/blob', '', 'https://raw.githubusercontent.com' + x.attrs['href'])
                try:
                    result[name] = {'scale': j.title(), 'url': url}
                except KeyError:
                    result[name] = [{'scale': j.title(), 'url': url}]

            with open('{} reddit table.txt'.format(j), 'w+') as outfile:
                for conf in FBS:
                    outfile.write('{}\n\n|S&P+ in {}|\n|:-:|\n'.format(conf.title(), j.title()))
                    outfile.write('|[{} in {}]({})|\n'.format(conf.title(), result[conf.title()]['scale'], result[conf.title()]['url']))
                    for team in result:
                        try:
                            if schedule[team.lower()]['conference'] == conf:
                                outfile.write('|[{} in {}]({})|\n'.format(team, result[team]['scale'], result[team]['url']))
                        except KeyError:
                            pass
                    outfile.write('\n\n')

        return out

    @staticmethod
    def get_spplus_stdv(
            url='https://www.sbnation.com/college-football/2018/2/9/16994486/2018-college-football-rankings-projections',
            schedule=None):
        '''
        The STDEV is needed for win probability calculations.
        :param url: the url to pull S&P+ from
        :param schedule: if specified, the local file that holds the S&P+ values
        :return: a float that represents the stdev of the S&P+ values.
        '''
        if schedule:
            # TODO: if the schedule file is specified, use those values
            pass
        else:
            spplus = [x['s&p+'] for x in Utils.scrape_spplus(url)]
        return (sum([(x - sum(spplus) / len(spplus)) ** 2 for x in spplus]) / len(spplus)) ** 0.5


Utils.scrape_png_links()
