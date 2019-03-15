import base64
import csv
import json
import os
import pprint
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup as bs

from defs import FBS, WEEKS
from poll import APPoll
from utils import Utils


class Schedule(object):
    def __init__(self, file=None, year=datetime.now().year):
        if file:
            self.file = file
            with open(file, 'r', encoding='utf8') as infile:
                self.data = json.load(infile)
        else:
            self.url = 'https://api.collegefootballdata.com/games?year={}'.format(year)
            self.download_schedules()

    def add_game(self, team, **kwargs):
        g = {x: kwargs[x] if x in kwargs else [] if x == "scoreBreakdown" else "" for x in
             ["canceled", "home-away", "id", "location", "opponent", "scoreBreakdown",
              "startDate", "startTime", "teamRank", "winner"] if x in kwargs}

        self.data[team]['schedule'].append(g)

    def box_score(self, game):
        opponent = game['opponent']

        try:
            opp_game = [x for x in self.data[opponent]['schedule'] if x['id'] == game['id']][0]
        except IndexError:
            raise IndexError
        # TODO: make this spit out a boxscore

    @staticmethod
    def clean_team_name(name, display: bool = False):
        # various data sources uses different aliases for the same team (much to my irritation) or special characters
        # this method will try to enforce some kind of sensible naming standard

        result = name.lower()

        # a dictionary of states or other abbreviations
        abbrv = {
            '&': '',
            'ak': 'alaska',
            'al': 'alabama',
            'ar': 'arkansas',
            'as': 'american samoa',
            'az': 'arizona',
            'ca': 'california',
            'caro': 'carolina',
            'co': 'colorado',
            'ct': 'connecticut',
            'conn': 'connecticut',
            'dc': 'district of columbia',
            'de': 'delaware',
            'fl': 'florida',
            '(fla.)': '',
            'ga': 'georgia',
            'gu': 'guam',
            'hi': 'hawaii',
            'ia': 'iowa',
            'id': 'idaho',
            'il': 'illinois',
            'ill': 'illinois',
            'in': 'indiana',
            'ks': 'kansas',
            'ky': 'kentucky',
            'la': 'louisiana',
            'ma': 'massachusetts',
            'md': 'maryland',
            'me': 'maine',
            'mi': 'michigan',
            'miss': 'mississippi',
            'mn': 'minnesota',
            'mo': 'missouri',
            'mp': 'northern mariana islands',
            'ms': 'mississippi',
            'mt': 'montana',
            'na': 'national',
            'nc': 'north caroli;na',
            'nd': 'north dakota',
            'ne': 'nebraska',
            'nh': 'new hampshire',
            'nj': 'new jersey',
            'nm': 'new mexico',
            'n.m.': 'new mexico',
            'nv': 'nevada',
            'ny': 'new york',
            'oh': 'ohio',
            'ok': 'oklahoma',
            'or': 'oregon',
            'pa': 'pennsylvania',
            'pr': 'puerto rico',
            'ri': 'rhode island',
            'sc': 'south carolina',
            'sd': 'south dakota',
            'st': 'state',
            'tn': 'tennessee',
            'tenn': 'tennessee',
            'tx': 'texas',
            'univ': '',
            'ut': 'utah',
            'va': 'virginia',
            'vi': 'virgin islands',
            'vt': 'vermont',
            'wa': 'washington',
            'wi': 'wisconsin',
            'wv': 'west virginia',
            'wy': 'wyoming',
            's': 'south',
            'se': 'southeastern'
        }

        for x in abbrv:
            result = re.sub(r'\b%s\b' % x, abbrv[x], result)

        # trim out any weird special characters (most likely periods) and convert to lower case
        result = re.sub(r'[^\w\s]', ' ', result).lower().strip()

        # remove any leading, trailing, or consecutive whitespaces
        result = re.sub(' +', ' ', result).strip()

        if display:
            if result == 'texas am':
                result = 'Texas A&M'
            elif result.split()[0] != 'utah' and (result[0] == 'u' or result[-1] == 'u'):
                result = result.upper()
            else:
                result = result.title()

        # TODO: build a structure of aliases so we can reference them
        '''
        # take the dictionary of aliases and attempt to find the best match
        for team, alts in enumerate(aliases):
            try:
                if len(get_close_matches(name, alts, n=1, cutoff=1)) > 0:
                    return team
                else:
                    raise Exception("No matches found for {}.".format(name))
            except Exception as error:
                print("An error occured: ".format(error))
                return None
        '''
        return result

    def cull(self):
        new = {}
        for t in self.data:
            # cull any games between fcs schools
            if self.data[t]['conference'] not in FBS:
                for i in range(len(self.data[t]['schedule'])):
                    opp = self.data[t]['schedule'][i]['opponent']
                    oconf = self.data[opp]['conference']
                    if oconf not in FBS:
                        del self.data[t]['schedule'][i]
            # cull any schools with empty schedules
            if len(self.data[t]['schedule']) > 0:
                new[t] = self.data[t]
        self.data = new

    def download_schedules(self, year=datetime.now().year) -> None:
        # get the schedule
        games = json.loads(requests.get(self.url).text)

        # build a list of teams
        self.data = {x: {} for x in set([y[z] for y in games for z in ['home_team', 'away_team']])}

        # populate the team data
        teams = json.loads(requests.get('https://api.collegefootballdata.com/teams').text)

        k = self.data.keys()

        for t in teams:
            if t['school'] in k:
                self.data[t['school']] = {x: t[x] for x in ['mascot', 'conference', 'division', 'color', 'alt_color']}
                self.data[t['school']]['schedule'] = []
                self.data[t['school']]['sp+'] = {}
                try:
                    self.data[t['school']]['logo'] = t['logos'][0]
                    response = requests.get(self.data[t['school']]['logo'], stream=True)
                    self.data[t['school']]['logoURI'] = base64.b64encode(response.raw.read()).decode()

                except TypeError:
                    print("no logo available for {}".format(t['school']))
                    pass

        # populate the team schedules
        for g in games:
            h = g['home_team']
            a = g['away_team']
            f = datetime.strptime(g['start_date'], '%Y-%m-%dT%X.000Z')
            d = f.strftime('%Y-%m-%d')
            t = f.strftime('%X')

            self.data[h]['schedule'].append({'canceled': 'false',
                                             'home-away': 'home',
                                             'id': g['id'],
                                             'location': g['venue'],
                                             'opponent': a,
                                             'scoreBreakdown': [x for x in g['home_line_scores']] if g[
                                                 'home_line_scores'] else [],
                                             'startDate': d,
                                             'startTime': t,
                                             'winner': 'true' if g['home_line_scores'] and g[
                                                 'away_line_scores'] and sum(
                                                 g['home_line_scores']) > sum(
                                                 g['away_line_scores']) else 'false'})

            self.data[a]['schedule'].append({'canceled': 'false',
                                             'home-away': 'away',
                                             'id': g['id'],
                                             'location': g['venue'],
                                             'opponent': h,
                                             'scoreBreakdown': [x for x in g['away_line_scores']] if g[
                                                 'away_line_scores'] else [],
                                             'startDate': d,
                                             'startTime': t,
                                             'winner': 'true' if g['away_line_scores'] and g[
                                                 'home_line_scores'] and sum(
                                                 g['away_line_scores']) > sum(
                                                 g['home_line_scores']) else 'false'})

    @staticmethod
    def export_game_times_from_raw(file, year=None):
        with open(file, 'r') as infile:
            data = json.load(infile)
        if not year:
            try:
                year = [x for x in file.split() if x.isdigit()][0]
            except KeyError:
                year = 'null'
        with open('{} game times.csv'.format(year), 'w+', newline='', encoding='utf8') as outfile:
            cw = csv.writer(outfile)
            cw.writerow(
                ['Home Team', 'Home Team Rank', 'Home Team Conference', 'Away Team', 'Away Team Rank',
                 'Away Team Conference', 'Conference Game?', 'Date',
                 'Time', 'Location'])
            for g in data:
                try:
                    home = g['home']['name_raw']
                except KeyError:
                    try:
                        home = g['home']['nameRaw']
                    except KeyError:
                        home = g['home']['name']
                try:
                    away = g['away']['name_raw']
                except KeyError:
                    try:
                        away = g['away']['nameRaw']
                    except KeyError:
                        away = g['away']['name']
                confs = g['conference'].split()[1:]
                if confs[0] == 'top-25':
                    confs = confs[1:]
                h_conf = confs[0]
                if len(confs) == 1:
                    a_conf = confs[0]
                    conf_game = True
                else:
                    a_conf = confs[1]
                    conf_game = False
                h_rank = g['home']['teamRank']
                a_rank = g['away']['teamRank']
                startTime = g['startTime']
                if len(startTime.split(':')[0]) == 1:
                    startTime = '0' + startTime
                if startTime.endswith('PM ET') and int(startTime.split(':')[0]) < 12:
                    startTime = str(int(startTime.split(':')[0]) + 12) + startTime[2:]
                match = re.compile('[a-zA-Z]').search(startTime)
                startTime = startTime[:match.start()].strip()
                if len(startTime) > 0:
                    startTime = datetime.strptime(startTime, '%H:%M').strftime('%H:%M')
                startDate = g['startDate']
                location = g['location']
                cw.writerow([home, h_rank, h_conf, away, a_rank, a_conf, conf_game, startDate, startTime, location])

    def export_game_results(self, file: str = 'out', fbs=False, conference=None):
        def find(t, o):
            try:
                for i, dict in enumerate(self.data[t]['schedule']):
                    if dict['opponent'] == o:
                        return i
            except KeyError:
                return -2
            return -1

        if not file.endswith('.csv'):
            file += '.csv'
        with open(file, 'w+', newline='') as outfile:
            cw = csv.writer(outfile)
            cw.writerow(['orig_team', 'dest_team', 'flow'])

            for team in self.data:
                try:
                    conf = self.data[team]['conference']
                except KeyError:
                    continue
                if conference:
                    if not conf.lower() == conference.lower():
                        continue
                if conf in FBS:
                    for i in range(len(self.data[team]['schedule'])):
                        opp = self.data[team]['schedule'][i]['opponent']
                        if conference:
                            if not self.data[opp]['conference'].lower() == conference.lower():
                                continue
                        if fbs:
                            try:
                                if self.data[opp]['conference'] not in FBS:
                                    continue
                            except KeyError:
                                continue
                        j = find(opp, team)
                        if j > 0:
                            pf = sum(self.data[team]['schedule'][i]['scoreBreakdown'])
                            pa = sum(self.data[opp]['schedule'][j]['scoreBreakdown'])
                            flow = pf - pa
                            cw.writerow([Schedule.clean_team_name(team, display=True),
                                         Schedule.clean_team_name(opp, display=True), flow])

    def export_stadium_names(self, file: str = 'stadiums'):
        if not file.endswith('.json'):
            file += '.json'

        result = {}

        for team in self.data:
            try:
                conf = self.data[team]['conference']
            except KeyError:
                conf = 'independent'
            if conf in FBS:
                name = Schedule.clean_team_name(team, display=True)
                result[name] = []
                for i in range(len(self.data[team]['schedule'])):
                    if self.data[team]['schedule'][i]['home-away'] == 'home' and self.data[team]['schedule'][i][
                        'location'] not in result[name]:
                        result[name].append(self.data[team]['schedule'][i]['location'])
        with open(file, 'w+') as outfile:
            json.dump(result, outfile, indent=4, sort_keys=True)

    def export_teams_by_division_and_conference(self, file: str = 'out'):
        result = []
        if not file.endswith('.csv'):
            file += '.csv'
        for team in self.data:
            try:
                conf = self.data[team]['conference']
            except KeyError:
                conf = 'independent'
            if conf in FBS:
                try:
                    div = self.data[team]['division']
                except KeyError:
                    div = ''
                color = self.data[team]['color']
                team = Schedule.clean_team_name(team, display=True)
                result.append([team, conf.title(), div.title(), color])
        result.sort(key=lambda x: (x[1], x[2], x[3]))
        with open(file, 'w+', newline='') as outfile:
            cw = csv.writer(outfile)
            cw.writerow(['team', 'conference', 'division'])
            for row in result:
                cw.writerow(row)

    @staticmethod
    def make_blank_schedule(year=None):
        with open('schedule.json', 'r', encoding='utf8') as infile:
            s = json.load(infile)
        for x in s:
            del s[x]['rankings']
            s[x]['schedule'] = []
            s[x]['sp+'] = {}

        if year:
            n = '{} schedule.json'.format(year)
        else:
            n = 'new schedule.json'
        with open(n, 'w+') as outfile:
            json.dump(s, outfile, indent=4, sort_keys=True)

    def normalize_schedule(self, method: str = 'spplus', week: int = -1):
        # A method to ensure that all games have a total win probability equal to one

        # local helper function to locate the opponent within the schedule
        def find(lst, team, opp):
            try:
                for i, dict in enumerate(lst[team]['schedule']):
                    if dict['opponent'] == opp:
                        return i
            except KeyError:
                return -2
            return -1

        for team in self.data:
            for i in range(len(self.data[team]['schedule'])):
                try:
                    win_prob = self.data[team]['schedule'][i][method]
                except KeyError:
                    continue
                if len(win_prob) > 0:
                    opponent = self.data[team]['schedule'][i]['opponent']
                    # Is this a opponent even in our json file?
                    if opponent not in self.data:
                        continue
                    opp_win_prob = round(1 - win_prob[week], 3)
                    # We have to find the correct index for the opponent
                    # because they may not play in the same order due to byes
                    j = find(self.data, opponent, team)

                    try:
                        if self.data[opponent]['schedule'][j][method][week] != opp_win_prob:
                            self.data[opponent]['schedule'][j][method][week] = opp_win_prob
                    except IndexError:
                        self.data[opponent]['schedule'][j][method].append(opp_win_prob)
                    except KeyError:
                        self.data[opponent]['schedule'][j][method] = [opp_win_prob]
                    except TypeError:
                        print('problem with {}, {}'.format(team, opponent))

    def populate_URIs(self):
        for file in os.listdir("./Resources"):
            if file.endswith(".jpg"):
                name = file[:-4].lower()
                with open(os.path.join("./Resources/", file), "rb") as imageFile:
                    uri = base64.b64encode(imageFile.read()).decode()
                    try:
                        self.data[name][file[:-4].lower()] = uri
                    except KeyError:
                        print("File for {}, but not found in schedule.".format(name, uri))

    def save_to_file(self, file=None):
        if not file:
            file = self.file

        if file == self.file:
            if input('Overwrite existing schedule file? Y/N: ')[0].lower() != 'y':
                file = input('New file name: ')
                if file[-5:] != '.json':
                    file += '.json'
                raise TypeError

        with open(file, 'w+', encoding='utf8') as outfile:
            json.dump(self.data, outfile, indent=4, sort_keys=True, ensure_ascii=False)

    @staticmethod
    def scrape_spplus(
            url='https://www.footballoutsiders.com/stats/ncaa2018'):
        result = []

        r = requests.get(url, headers=Utils.headers)

        for row in bs(r.text).findAll('tr')[1:]:
            cells = row.findAll('td')
            if cells[0].text != 'Team':
                result.append({'name': cells[0].text, 'sp+': float(cells[4].text)})

        return result

    def report_week(self, week=-1):
        if not week:
            date = max(
                datetime.strptime(w[1], '%Y-%m-%d') for w in WEEKS if
                datetime.strptime(w[1], '%Y-%m-%d') <= datetime.now()).strftime('%Y-%m-%d')
            week = [x[1] for x in WEEKS].index(date) + 1
        elif 0 < week < len(WEEKS):
            pass
        else:
            raise ValueError("invalid week")
        output = []

        teams = [x for x in self.data]
        while len(teams) > 0:
            game = self.data[teams[0]]['schedule'][week]
            date = datetime.strptime(game['startDate'], '%Y=%m-%d')
            if WEEKS[week][0] <= date <= WEEKS[week][1]:
                output.append(self.boxscore(game))
            if game['opponent'] in teams:
                teams.pop(teams['opponent'])

    def update_from_NCAA(self, new=None):
        def find(t):
            for x in self.data:
                if t == self.data[x]['nameRaw']:
                    return x
            return None

        if not new:
            new = Schedule.download_schedules()
        else:
            with open(new, 'r') as infile:
                new = json.load(infile)

        keys = {'canceled', 'home-away', 'location', 'opponent', 'scoreBreakdown', 'startDate', 'startTime', 'winner'}
        for game in new:
            away = find(game['away']['nameRaw'])
            if away and self.data[away]['conference'] in FBS:
                found = False
                try:
                    for i in range(len(self.data[away]['schedule'])):
                        if self.data[away]['schedule'][i]['id'] == game['id']:
                            found = True
                            try:
                                if self.data[away]['schedule'][i]['doNotUpdate']:
                                    continue
                            except KeyError:
                                pass
                            for key in ['startDate', 'startTime']:
                                self.data[away]['schedule'][i][key] = game[key]
                            for key in ['scoreBreakdown', 'teamRank', 'winner']:
                                self.data[away]['schedule'][i][key] = game['away'][key]
                            try:
                                self.data[away]['schedule'][i]['scoreBreakdown'] = [int(x) if len(x) > 0 else 0
                                                                                    for x in
                                                                                    self.data[away]['schedule'][i][
                                                                                        'scoreBreakdown']]
                            except ValueError as e:
                                print("problem with scores for {}".format(away))
                                pass
                            break
                except KeyError as e:
                    print("couldn't find {}".format(e))
                    pass
                if not found:
                    foo = {x: None for x in keys}
                    foo['canceled'] = 'false'
                    foo['home-away'] = 'away'
                    foo['location'] = game['location']
                    foo['opponent'] = game['home']['nameSeo']
                    try:
                        foo['scoreBreakdown'] = [int(x) if len(x) > 0 else 0 for x in game[away]['scoreBreakdown']]
                    except KeyError as e:
                        print(e)
                    foo['startDate'] = game['startDate']
                    foo['startTime'] = game['startTime']
                    foo['winner'] = game['away']['winner']
                    self.data[away]['schedule'].append(foo)

            home = find(game['home']['nameRaw'])
            if home and self.data[home]['conference'] in FBS:
                found = False
                try:
                    for i in range(len(self.data[home]['schedule'])):
                        if self.data[home]['schedule'][i]['id'] == game['id']:
                            found = True
                            try:
                                if self.data[home]['schedule'][i]['doNotUpdate']:
                                    continue
                            except KeyError:
                                pass
                            for key in ['startDate', 'startTime']:
                                self.data[home]['schedule'][i][key] = game[key]
                            for key in ['scoreBreakdown', 'teamRank', 'winner']:
                                self.data[home]['schedule'][i][key] = game['home'][key]
                            try:
                                self.data[home]['schedule'][i]['scoreBreakdown'] = [int(x) if len(x) > 0 else 0
                                                                                    for x in
                                                                                    self.data[home]['schedule'][i][
                                                                                        'scoreBreakdown']]
                            except ValueError as e:
                                print("problem with scores for {}".format(away))
                                pass

                            break
                except KeyError as e:
                    print("couldn't find {}".format(e))
                    pass
                if not found:
                    foo = {x: None for x in keys}
                    foo['canceled'] = 'false'
                    foo['home-away'] = 'home'
                    foo['location'] = game['location']
                    foo['opponent'] = game['away']['nameSeo']
                    try:
                        foo['scoreBreakdown'] = [int(x) if len(x) > 0 else 0 for x in game[home]['scoreBreakdown']]
                    except KeyError as e:
                        print(e)
                    foo['startDate'] = game['startDate']
                    foo['startTime'] = game['startTime']
                    foo['winner'] = game['home']['winner']
                    self.data[home]['schedule'].append(foo)

    def update_game(self, game_id, field, new_val):
        c = 0

        def find_game(t, g):
            for j in range(len(self.data[t]['schedule'])):
                if self.data[t]['schedule'][j]['id'] == str(g):
                    if field in self.data[t]['schedule'][j]:
                        self.data[t]['schedule'][j][field] = new_val
                        return 1
                    else:
                        return -1
            return 0

        for team in self.data:
            res = find_game(team, game_id)
            c += res
            if res >= 0:
                continue
            else:
                print('Not a valid field choice: {}'.format(field))
                return

        print('Found {} occurrences of game id {} '.format(c, game_id))

    def update_rankings(self, year=datetime.now().year, week=None) -> None:
        if not week:
            date = max(
                datetime.strptime(w[1], '%Y-%m-%d') for w in WEEKS if
                datetime.strptime(w[1], '%Y-%m-%d') <= datetime.now()).strftime('%Y-%m-%d')
            week = [x[1] for x in WEEKS].index(date) + 1
        elif 0 < week < len(WEEKS):
            date = WEEKS[week][1]
        else:
            raise ValueError("invalid week")
        print('Retrieving AP poll for {} week {}'.format(year, week))
        ap = APPoll(week=week, year=year)
        ap.scrape()
        date = ap.ballots['date']
        print('poll published on {}'.format(date))
        not_in_poll = []
        copy = dict(ap.ballots['results'])
        for team in self.data:
            if date not in self.data[team]['rankings']['AP'].keys():
                self.data[team]['rankings']['AP'][date] = {'overall': -1, 'voters': {}}

            # cross reference the teams to the keys used by the AP
            if team == 'texas am':
                key = 'Texas A&M'
            elif team == 'byu':
                key = 'Brigham Young'
            elif team == 'ole miss':
                key = 'Mississippi'
            elif team.split()[0] != 'utah' and (team[0] == 'u' or team[-1] == 'u'):
                key = team.upper()
            else:
                key = team.title()

            try:
                self.data[team]['rankings']['AP'][date]['overall'] = ap.ballots['results'][key]['rank']
                for v in ap.ballots['voters']:
                    if key in ap.ballots['voters'][v]['rankings']:
                        self.data[team]['rankings']['AP'][date]['voters'][v] = {
                            'outlet': ap.ballots['voters'][v]['outlet'],
                            'rank': ap.ballots['voters'][v]['rankings'].index(key) + 1}

                del ap.ballots['results'][key]
            except KeyError:
                not_in_poll.append(team)
        pp = pprint.PrettyPrinter(indent=4)
        if len(ap.ballots['results']) > 0:
            print('Portions of the poll couldn\'t be found:')
            pp.pprint(ap.ballots['results'])
        response = ''
        while len(response) == 0:
            response = input('Display the full AP results? (Y/N) ')
        if response[0].lower() == 'y':
            pp.pprint(copy)

        if input('Display teams not found in the AP Poll? (Y/N) ')[0].lower() == 'y':
            print('Teams not appearing in the AP poll:')
            pp.pprint(not_in_poll)

    def update_spplus(self):
        new = Schedule.scrape_spplus()

        for team in new:
            try:
                if team['name'] == 'Central Florida':
                    team['name'] = 'UCF'
                elif team['name'] == 'Miami-FL':
                    team['name'] = 'Miami'
                elif team['name'] == 'Texas A&M':
                    team['name'] = 'Texas AM'
                elif team['name'] == 'NC State':
                    team['name'] = 'North Carolina State'
                elif team['name'] == 'Southern Miss':
                    team['name'] = 'Southern Mississippi'
                elif team['name'] == 'Miami-OH':
                    team['name'] = 'Miami Ohio'
                elif team['name'] == 'UL-Lafayette':
                    team['name'] = 'Louisiana'
                elif team['name'] == 'Massachusetts':
                    team['name'] = 'UMass'
                elif team['name'] == 'UL-Monroe':
                    team['name'] = 'Louisiana Monroe'
                elif team['name'] == 'UTSA':
                    team['name'] = 'UT San Antonio'
                elif team['name'] == 'Connecticut':
                    team['name'] = 'Uconn'
                self.data[team['name'].lower()]['sp+'][datetime.now().strftime("%Y-%m-%d")] = team['sp+']
            except KeyError:
                print(team)

    def to_csv(self, csv_file):
        with open(csv_file, 'w+', newline='') as outfile:
            csvwriter = csv.writer(outfile)
            count = 0
            for elem in self.data:
                if count == 0:
                    csvwriter.writerow(
                        ['home', 'away', 'startDate', 'startTime', 'location', 'conference', 'url', ])
                    count += 1
                else:
                    row = []
                    for val in ['home', 'away', 'startDate', 'startTime', 'location', 'conference', 'url', ]:
                        if val == 'home' or val == 'away':
                            row.append(elem[val]['nameRaw'])
                        elif val == 'conference':
                            row.append(' vs. '.join(elem[val].split(' ')[1:]))
                        elif val == 'url':
                            row.append('www.ncaa.com' + elem[val])
                        else:
                            row.append(elem[val])
                    csvwriter.writerow(row)


s = Schedule(file='2019foo.json')
for t in s.data:
    if len(s.data[t]['sp+'])==0:
        print(t)
'''
s = Schedule(file='schedule.json')
s.update_spplus()
s.save_to_file()
'''
