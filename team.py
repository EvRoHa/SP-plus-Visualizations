import csv
import os
from datetime import datetime

from defs import WEEKS
from graph import Graph
from utils import Utils


class Team:
    def __init__(self, name=None, schedule=None):
        self.schedule = schedule

        if not name:
            self.name = ""
        else:
            assert isinstance(name, str), "Name is not a string!"
            self.name = name.lower()
            self.conference = self.schedule[self.name]['conference']
            self.expected_wins = self.schedule[self.name]['sp+ expected wins']
            self.logo_URI = self.schedule[self.name]['logoURI']
            self.spplus = self.schedule[self.name]['sp+']
            self.win_probabilities = {}
            for x in self.spplus:
                cur = self.spplus[x]
                self.win_probabilities[x] = []
                date = datetime.strptime(x, "%Y-%m-%d")
                for i in range(len(self.schedule[self.name]['schedule'])):
                    opp_sp = self.schedule[self.schedule[self.name]['schedule'][i]['opponent']]['sp+']
                    best_match = max(
                        datetime.strptime(dt, '%Y-%m-%d') for dt in opp_sp.keys() if
                        datetime.strptime(dt, '%Y-%m-%d') <= date).strftime('%Y-%m-%d')
                    osp = opp_sp[best_match]
                    loc = self.schedule[self.name]['schedule'][i]['home-away']
                    self.win_probabilities[x].append(Utils.calculate_win_prob_from_spplus(cur, osp, loc))

            # If a game was already played, assign 100% or 0% win probability
            for x in range(len(self.schedule[self.name]['schedule'])):
                start = datetime.strptime(self.schedule[self.name]['schedule'][x]['startDate'], '%Y-%m-%d')
                if start < datetime.now():
                    if self.schedule[self.name]['schedule'][x]['winner'] == 'true':
                        out = 1.0
                    else:
                        out = 0.0
                    for i in [x for x in self.win_probabilities.keys() if datetime.strptime(x, '%Y-%m-%d') >= start]:
                        self.win_probabilities[i][x] = out

            try:
                self.primary_color = Utils.hex_to_rgb(self.schedule[self.name]['primaryColor'])
                self.secondary_color = Utils.hex_to_rgb(self.schedule[self.name]['secondaryColor'])
            except KeyError:
                self.primary_color = Utils.hex_to_rgb(self.schedule[self.name]['color'])
                self.secondary_color = Utils.hex_to_rgb(self.schedule[self.name]['color'])
            # Not all teams have a conference, not all conferences have divisions
            try:
                self.division = self.schedule[self.name]['division']
            except KeyError:
                self.division = "none"

    def get_played_games(self):
        # Determine which games were already played and record the score for those that were
        played = []
        for x in self.schedule[self.name]['schedule']:
            pf = sum(x['scoreBreakdown'])
            pa = 0
            for y in self.schedule[x['opponent']]['schedule']:
                if x['id'] == y['id']:
                    pa = sum(y['scoreBreakdown'])
            if datetime.strptime(x['startDate'], '%Y-%m-%d') < datetime.now():
                played.append([pf, pa, x['winner']])
            else:
                played.append(None)
        return played

    def make_win_probability_graph(self, file='out', hstep=50, vstep=50, margin=5, logowidth=40, logoheight=40,
                                   menuheight=40, absolute=False, old=None, week=0, method='sp+', scale='red-green'):

        start, end = datetime.strptime(WEEKS[week][0], '%Y-%m-%d'), datetime.strptime(WEEKS[week][1], '%Y-%m-%d')

        try:
            best_match = max(
                datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys() if
                start <= datetime.strptime(dt, '%Y-%m-%d') <= end).strftime('%Y-%m-%d')
        except ValueError:
            best_match = max(datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys()).strftime(
                '%Y-%m-%d')

        cur_win_prob = self.win_probabilities[best_match]

        start, end = datetime.strptime(WEEKS[week - 1][0], '%Y-%m-%d'), datetime.strptime(WEEKS[week - 1][1],
                                                                                          '%Y-%m-%d')

        try:
            best_match = max(
                datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys() if
                start <= datetime.strptime(dt, '%Y-%m-%d') <= end).strftime('%Y-%m-%d')
        except ValueError:
            best_match = max(datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys()).strftime(
                '%Y-%m-%d')

        last_win_prob = self.win_probabilities[best_match]

        record = self.project_win_totals(week=week - 1)
        played = self.get_played_games()
        if old:
            prior = self.project_win_totals(week - 2)
        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {} - {}.svg'.format(file, method, scale))

        if not old:
            rows = 1 + len(cur_win_prob)
            cols = 5 + len(cur_win_prob)
        else:
            rows = 1 + len(cur_win_prob)
            cols = 6 + len(cur_win_prob)

        graph = Graph(path=path, width=hstep * cols + 2 * margin, height=vstep * rows + 4 * margin + menuheight)

        # Add the team logo
        try:
            graph.add_image(margin + (hstep - logowidth) / 2,
                            margin + (vstep - logoheight) / 2,
                            logowidth,
                            logoheight,
                            self.schedule[self.name]['logoURI'])
        except IndexError:
            pass

        # Add the horizontal header label; it is at the very top of the svg and
        # covers the right 16 columns, with centered text
        graph.add_text(margin + hstep * (cols - (cols - 4) / 2),
                       margin + vstep * 0.5 - 4,
                       alignment='middle', text='Total Wins as projected by {}'.format(method.upper()))

        if not week or week == 0:
            first_week, second_week = 0, 0
        else:
            first_week = week - 1
            second_week = week

        graph.add_text(margin + hstep * (cols - (cols - 4) / 2),
                       margin + vstep * 0.5 + 9, size=13,
                       alignment='middle', text='(change from week {} to week {})'.format(first_week, second_week))

        # Add column labels for the Week, H/A and Opp
        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5, size=13, text='Week')
        graph.add_text(margin + hstep * 1.5, margin + vstep * 1.5, size=13, text='H/A')
        graph.add_text(margin + hstep * 2.5, margin + vstep * 1.5, size=13, text='OPP')

        # Add column labels for the Win Prob and (change)
        graph.add_text(margin + hstep * 3.5, margin + vstep * 1.5 - 3, size=10, text='Win Prob')
        graph.add_text(margin + hstep * 3.5, margin + vstep * 1.5 + 9, size=10, text='(change)')

        # Make the color-coded body of the table
        for i in range(0, rows - 1):
            # find the max and min in this week to determine color of cell
            # The rows can be color coded by giving scaling to the maximum likelihood within the week (relative)
            # or by absolute likelihood (max=1.0). Default is relative.
            if absolute:
                upper, lower = 1, 0
            else:
                upper, lower = max(record[i]), min(record[i])

            for j in range(0, len(record) + 1):
                # where wins <= games played, make the table
                if j < len(record[i]):
                    if absolute:
                        r, g, b = Utils.gradient_color(0, 1, record[i][j], scale=scale,
                                                       primaryColor=self.primary_color,
                                                       secondaryColor=self.secondary_color)
                    else:
                        r, g, b = Utils.gradient_color(lower, upper, record[i][j], scale=scale,
                                                       primaryColor=self.primary_color,
                                                       secondaryColor=self.secondary_color)

                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (4 + j), margin + vstep * (2 + i), hstep, vstep, color='none',
                                   fill=(r, g, b))

                    # Should the text be white or black?
                    text_color = Utils.get_text_contrast_color(r, g, b)

                    graph.add_text(margin + hstep * (4.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   alignment='middle', color=text_color,
                                   text=str(round(100 * record[i][j], 1)) + '%')

                    if old:
                        diff = round(100 * (prior[i][j] - record[i][j]), 1)
                        if diff > 0:
                            txt = '(+{})%'.format(diff)
                        elif diff < 0:
                            txt = '(' + str(diff) + '%)'
                        else:
                            txt = '(+' + str(diff) + '%)'
                        # Write the probability change in the box
                        graph.add_text(margin + hstep * (4.5 + j), margin + vstep * (2.5 + i) + 8, alignment='middle',
                                       color=text_color, size=10, text=txt)

                    # Write the cumulative probability in the box
                    graph.add_text(0.8 * margin + hstep * (5 + j),
                                   vstep * (3 + i),
                                   alignment='middle', anchor='end', color=text_color, size=8,
                                   text=str(round(abs(100 * (1 - sum(record[i][x] for x in range(0, j)))), 1)) + '%')

                else:
                    # Draw a gray box
                    graph.add_rect(margin + hstep * (4 + j), margin + vstep * (2 + i), hstep, vstep,
                                   color='none', fill=(150, 150, 150))

            if old:
                j = len(record) + 1
                old_xw = sum(x * prior[i][x] for x in range(len(prior[i])))
                new_xw = sum(x * record[i][x] for x in range(len(record[i])))
                diff = round(new_xw - old_xw, 1)
                if diff > 0:
                    txt = '(+{})'.format(diff)
                    r, g, b = 0, 205, 0
                    weight = 'bolder'
                elif diff < 0:
                    txt = '(' + str(diff) + ')'
                    r, g, b = 255, 77, 77
                    weight = 'bolder'
                else:
                    txt = '(+0.0)'
                    r, g, b = 0, 0, 0
                    weight = 'normal'

                # What's the win expectation?
                graph.add_text(margin + hstep * (4.5 + j), margin + vstep * (2.5 + i) - 2, alignment='middle',
                               color=(r, g, b), size=13,
                               text=round(new_xw, 1))

                # How did the win expectation change?
                graph.add_text(margin + hstep * (4.5 + j), margin + vstep * (2.5 + i) + 8, alignment='middle',
                               color=(r, g, b), size=10,
                               text=txt, weight=weight)

        for i in range(0, rows - 1):
            if played[i]:
                if played[i][2] == 'true':
                    wl = 'WON'
                else:
                    wl = 'LOST'
                # summarize the game
                graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i) - 3, alignment='central', text=wl)

                graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i) + 12,
                               text='{} - {}'.format(*played[i][0:2]))

            elif old:
                diff = round(100 * last_win_prob[i] - 100 * cur_win_prob[i],
                             1)
                if diff > 0:
                    txt = '(+{}%)'.format(diff)
                    r, g, b = 0, 205, 0
                    weight = 'bolder'
                elif diff < 0:
                    txt = '(' + str(diff) + '%)'
                    r, g, b = 255, 77, 77
                    weight = 'bolder'
                else:
                    txt = '(+0.0%)'
                    r, g, b = 0, 0, 0
                    weight = 'normal'

                # Add the probability text in the prob column
                graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i) - 2,
                               alignment='middle', text=round(100 * cur_win_prob[i], 1))

                # Write the probability change in the box
                graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i) + 8, alignment='middle',
                               color=(r, g, b), size=10, text=txt,
                               weight=weight)

            else:
                graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i),
                               alignment='central', text=round(100 * cur_win_prob[i], 1))

        for j in range(0, len(record) + 1):
            if j != 1:
                txt = 'Wins'
            else:
                txt = 'Win'
            # Add the column label
            graph.add_text(margin + hstep * (4.5 + j), margin + vstep * 1.5, alignment='middle', size=13,
                           text='{} {}'.format(j, txt))
        if old:
            # Add the column label
            graph.add_text(margin + hstep * (len(record) + 5.5), margin + vstep * 1.5 - 10, alignment='middle', size=10,
                           text='Expected')
            graph.add_text(margin + hstep * (len(record) + 5.5), margin + vstep * 1.5, alignment='middle', size=10,
                           text='Wins')
            graph.add_text(margin + hstep * (len(record) + 5.5), margin + vstep * 1.5 + 10, alignment='middle', size=10,
                           text='(change)'.format(j))

            for i in range(2, rows + 1):
                # add the horizontal lines between the rows
                graph.add_line(x1=margin, y1=margin + vstep * i, x2=margin + hstep * cols, y2=vstep * i + margin)
            for j in range(1, cols):
                # add the vertical lines between the columns
                graph.add_line(x1=margin + hstep * j, y1=margin + vstep, x2=margin + hstep * j,
                               y2=vstep * (rows + 1) + margin)

            # Add the home / away data
            for i in range(0, rows - 1):
                if self.schedule[self.name]['schedule'][i]['home-away'] == 'home':
                    loc = 'vs'
                else:
                    loc = '@'

                graph.add_text(margin + hstep * 1.5, margin + vstep * (2.5 + i), alignment='middle', size=13,
                               text=loc)

                # Add the opponent logo
                try:
                    opponent = self.schedule[self.name]['schedule'][i]['opponent']
                    graph.add_image(2 * hstep + margin + (hstep - logowidth) / 2,
                                    vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                                    self.schedule[opponent]['logoURI'])

                except KeyError:
                    pass

                # Add the row week label
                graph.add_text(margin + hstep * 0.5, margin + vstep * (2.5 + i), alignment='middle', size=13,
                               text=i + 1)

            # Draw the outline box for the table
            graph.add_rect(margin, margin + vstep, hstep * cols, vstep * (rows), fill='none', stroke_width=2)

            # Draw the outline box for the win total sub-table
            graph.add_rect(margin + hstep * 4, margin + vstep, hstep * (cols - 4), vstep * (rows), fill='none',
                           stroke_width=2)

            # Draw the outline box for the column headers
            graph.add_rect(margin, margin + vstep, hstep * cols, vstep, fill='none', stroke_width=2)

            # Draw the outline box for the win total header label
            graph.add_rect(margin + hstep * 4, margin, hstep * (cols - 4), vstep, fill='none', stroke_width=2)

            graph.write_file()

    def project_win_totals(self, week=-1):
        if (week < 0) or (week > len(self.win_probabilities)):
            week = -1

        start, end = datetime.strptime(WEEKS[week][0], '%Y-%m-%d'), datetime.strptime(WEEKS[week][1], '%Y-%m-%d')

        try:
            best_match = max(
                datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys() if
                start <= datetime.strptime(dt, '%Y-%m-%d') <= end).strftime('%Y-%m-%d')
        except ValueError:
            best_match = max(datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys()).strftime(
                '%Y-%m-%d')

        win_probs = [x for x in self.win_probabilities[best_match]]

        # Make a ragged table to store 'games' x 'wins'
        record = [[0 for y in range(0, x + 1)] for x in range(1, len(win_probs) + 1)]
        record[0][0] = 1 - win_probs[0]  # first game was a loss
        record[0][1] = win_probs[0]  # first game was a win

        for i in range(1, len(record)):
            for j in range(0, i + 1):
                record[i][j] += record[i - 1][j] * (1 - win_probs[i])  # newest game was a loss
                record[i][j + 1] += record[i - 1][j] * (win_probs[i])  # newest game was a win

        return record

    def write_win_probability_csv(self, file='out'):
        record = self.project_win_totals()
        with open("{}.csv".format(file), 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(record)
