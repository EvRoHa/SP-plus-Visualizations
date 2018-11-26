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
            self.logo_URI = self.schedule[self.name]['logoURI']
            self.spplus = self.schedule[self.name]['sp+']
            best_match = max(
                datetime.strptime(dt, '%Y-%m-%d') for dt in self.spplus.keys() if
                datetime.strptime(dt, '%Y-%m-%d') <= datetime.now()).strftime('%Y-%m-%d')

            self.latest_spplus = self.schedule[self.name]['sp+'][best_match]

            # Create an array of individual game win probabilities
            # Each vector corresponds to an entry in the S&P+ values list, indicating chronological change
            self.win_probabilities = {}
            for x in self.spplus:
                cur = self.spplus[x]
                self.win_probabilities[x] = []
                date = datetime.strptime(x, "%Y-%m-%d")
                for i in range(len(self.schedule[self.name]['schedule'])):
                    # Get the opponent S&P+ value
                    opp_sp = self.schedule[self.schedule[self.name]['schedule'][i]['opponent']]['sp+']
                    # Use the most recent S&P+ values prior to the specified date
                    # Note there might be a misalignment between the S&P+ value dates for different teams, especially FCS teams
                    best_match = max(
                        datetime.strptime(dt, '%Y-%m-%d') for dt in opp_sp.keys() if
                        datetime.strptime(dt, '%Y-%m-%d') <= date).strftime('%Y-%m-%d')
                    osp = opp_sp[best_match]
                    # Who has the 2.5 point home field advantage?
                    loc = self.schedule[self.name]['schedule'][i]['home-away']
                    # Calculate the win probability and record it
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

    @staticmethod
    def expected_wins(vec):
        return sum(x * vec[x] for x in range(len(vec)))

    def get_best_sp_match(self, week):
        start, end = datetime.strptime(WEEKS[week - 1][0], '%Y-%m-%d'), datetime.strptime(WEEKS[week - 1][1],
                                                                                          '%Y-%m-%d')
        try:
            date = max(
                datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys() if
                start <= datetime.strptime(dt, '%Y-%m-%d') <= end).strftime('%Y-%m-%d')
        except ValueError:
            date = max(datetime.strptime(dt, '%Y-%m-%d') for dt in self.win_probabilities.keys() if
                       datetime.strptime(dt, '%Y-%m-%d') <= end).strftime('%Y-%m-%d')
        return date

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
                if x['canceled'] == 'true':
                    status = 'canceled'
                else:
                    status = x['winner']
                played.append([pf, pa, status])
            else:
                played.append(None)
        return played

    def make_win_probability_graph(self, file='out', hstep=50, vstep=50, margin=5, logowidth=40, logoheight=40,
                                   menuheight=40, absolute=False, old=None, week=0, method='sp+', scale='red-green'):

        cur_date = self.get_best_sp_match(week=week)
        cur_win_prob = self.win_probabilities[cur_date]
        cur_sp = self.spplus[cur_date]

        last_date = self.get_best_sp_match(week=week - 1)
        last_win_prob = self.win_probabilities[last_date]
        last_sp = self.spplus[last_date]
        record = self.project_win_totals(week=week)
        played = self.get_played_games()

        if old:
            prior = self.project_win_totals(week - 1)
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

        # Add the S&P+ value
        if cur_sp > 0:
            txt = '+{}'.format(cur_sp)
        else:
            txt = str(cur_sp)
        graph.add_text(margin + hstep,
                       margin + vstep / 2 - 10,
                       size=13,
                       alignment='middle', anchor='left', text='SP+: {}'.format(txt))
        graph.add_text(margin + hstep,
                       margin + vstep / 2,
                       size=8,
                       alignment='middle', anchor='left', text='as of {}'.format(cur_date))
        if cur_sp - last_sp > 0:
            txt = '+' + str(round(cur_sp - last_sp, 1))
        else:
            txt = str(round(cur_sp - last_sp, 1))
        graph.add_text(margin + hstep,
                       margin + vstep / 2 + 10,
                       size=8,
                       alignment='middle', anchor='left', text='Change from {}: {}'.format(last_date, txt))

        # Add the horizontal header label; it is at the very top of the svg and
        # covers the right 16 columns, with centered text
        graph.add_text(margin + hstep * (cols - (cols - 3) / 2),
                       margin + vstep * 0.5 - 4, size=13,
                       alignment='middle', text='Total Wins as projected by {}'.format(method.upper()))

        if not week or week == 0:
            first_week = 0
        else:
            first_week = week - 1

        graph.add_text(margin + hstep * (cols - (cols - 3) / 2),
                       margin + vstep * 0.5 + 9, size=13,
                       alignment='middle', text='(change after week {} games)'.format(first_week))

        # Add column labels for the Week, H/A and Opp
        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5, alignment='middle', size=13, text='When?')
        graph.add_text(margin + hstep * 1.5, margin + vstep * 1.5, alignment='middle', size=13, text='Where?')
        graph.add_text(margin + hstep * 2.5, margin + vstep * 1.5, alignment='middle', size=13, text='OPP')
        graph.add_text(0.8 * margin + hstep * 4, vstep * 2, alignment='middle', anchor='end', size=8, text='Opp. SP+')

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
                        diff = round(100 * (record[i][j] - prior[i][j]), 1)
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
                old_xw = Team.expected_wins(prior[i])
                new_xw = Team.expected_wins(record[i])
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
                if played[i][2] == 'canceled':
                    graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i), alignment='central', size=9,
                                   text='CANCELED')
                else:
                    if played[i][2] == 'true':
                        wl = 'WON'
                    else:
                        wl = 'LOST'
                    # summarize the game
                    graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i) - 3, alignment='central', text=wl)

                    graph.add_text(margin + hstep * 3.5, margin + vstep * (2.5 + i) + 12,
                                   text='{} - {}'.format(*played[i][0:2]))

            else:
                # Add the opponent S&P+ value
                opp_sp = self.schedule[self.schedule[self.name]['schedule'][i]['opponent']]['sp+']
                # Use the most recent S&P+ values prior to the specified date
                # Note there might be a misalignment between the S&P+ value dates for different teams, especially FCS teams
                d = datetime.strptime(cur_date, '%Y-%m-%d')
                date = max(
                    datetime.strptime(dt, '%Y-%m-%d') for dt in opp_sp.keys() if
                    datetime.strptime(dt, '%Y-%m-%d') <= d).strftime('%Y-%m-%d')
                osp = opp_sp[date]
                if osp > 0:
                    txt = '+{}'.format(osp)
                    r, g, b = 0, 205, 0
                    weight = 'bolder'
                elif osp < 0:
                    txt = str(osp)
                    r, g, b = 255, 77, 77
                    weight = 'bolder'
                else:
                    txt = str(osp)
                    r, g, b = 0, 0, 0
                    weight = 'normal'

                graph.add_text(0.5 * margin + hstep * 4, vstep * (3 + i), alignment='middle', anchor='end', size=8,
                               weight=weight, color=(r, g, b), text=txt)
                if old:
                    diff = round(100 * (cur_win_prob[i] - last_win_prob[i]), 1)
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
                                   alignment='middle', text=str(round(100 * cur_win_prob[i], 1)) + '%')

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
            graph.add_text(margin + hstep * (4.5 + j), margin + vstep * 1.5 - 7, alignment='middle', size=13,
                           text=j)
            graph.add_text(margin + hstep * (4.5 + j),
                           margin + vstep * 1.5 + 7,
                           size=13,
                           alignment='middle',
                           text=txt)

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
                loc = 'HOME'
            else:
                loc = 'AWAY'

            graph.add_text(margin + hstep * 1.5, margin + vstep * (2.5 + i) - 8, alignment='middle', size=13,
                           text=loc)

            # Get the game location
            loc = self.schedule[self.name]['schedule'][i]['location'].split(',')[-2:]
            graph.add_text(margin + hstep * 1.5, margin + vstep * (2.5 + i) + 2, alignment='middle', size=8,
                           text=loc[0])
            graph.add_text(margin + hstep * 1.5, margin + vstep * (2.5 + i) + 12, alignment='middle', size=8,
                           text=loc[1])

            # Add the opponent logo
            try:
                opponent = self.schedule[self.name]['schedule'][i]['opponent']
                graph.add_image(2 * hstep + margin + (hstep - logowidth) / 2,
                                vstep * (2 + i) + margin + (vstep - logoheight) / 2, logowidth, logoheight,
                                self.schedule[opponent]['logoURI'])
            except KeyError:
                pass

            # Add the row week label
            graph.add_text(margin + hstep * 0.5, margin + vstep * (2.5 + i) - 8, alignment='middle', size=10,
                           text='Week ' + str(i + 1))

            # Add the date and time
            d = self.schedule[self.name]['schedule'][i]['startDate']
            t = self.schedule[self.name]['schedule'][i]['startTime']
            graph.add_text(margin + hstep * 0.5, margin + vstep * (2.5 + i) + 2, alignment='middle', size=8,
                           text=d)
            if t == 'TBA':
                t = 'Time TBA'
            graph.add_text(margin + hstep * 0.5, margin + vstep * (2.5 + i) + 12, alignment='middle', size=8,
                           text=t)

            # Draw the outline box for the table
            graph.add_rect(margin, margin + vstep, hstep * cols, vstep * (rows), fill='none', stroke_width=2)

            # Draw the outline box for the win total sub-table
            graph.add_rect(margin + hstep * 4, margin + vstep, hstep * (cols - 4), vstep * (rows), fill='none',
                           stroke_width=2)

            # Draw the outline box for the column headers
            graph.add_rect(margin, margin + vstep, hstep * cols, vstep, fill='none', stroke_width=2)

            # Draw the outline box for the win total header label
            graph.add_rect(margin + hstep * 4, margin, hstep * (cols - 5), vstep, fill='none', stroke_width=2)

        graph.write_file()

    def project_win_totals(self, week=None, date=None):
        if not week or (week > len(self.win_probabilities)):
            week = -1

        if not date:
            best_match = self.get_best_sp_match(week)
        else:
            best_match = date

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

    def make_retrospective_projection_graph(self, file='out', hstep=50, vstep=50, margin=5, logowidth=40, logoheight=40,
                                   menuheight=40, absolute=False, method='sp+', scale='red-green'):
        win_probs = []
        for date in self.spplus:
            win_probs.append([date, self.spplus[date], self.project_win_totals(date=date)[-1]])

        width = max([len(x[2]) for x in win_probs])
        length = len(win_probs)
        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {} - {} - RETROSPECTIVE.svg'.format(file, method, scale))

        rows = 1 + length
        cols = 3 + width

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
        # TODO: change this block to give the gradient
        '''
        # Add the S&P+ value
        if cur_sp > 0:
            txt = '+{}'.format(cur_sp)
        else:
            txt = str(cur_sp)
        graph.add_text(margin + hstep,
                       margin + vstep / 2 - 10,
                       size=13,
                       alignment='middle', anchor='left', text='SP+: {}'.format(txt))
        graph.add_text(margin + hstep,
                       margin + vstep / 2,
                       size=8,
                       alignment='middle', anchor='left', text='as of {}'.format(cur_date))
        if cur_sp - last_sp > 0:
            txt = '+' + str(round(cur_sp - last_sp, 1))
        else:
            txt = str(round(cur_sp - last_sp, 1))
        graph.add_text(margin + hstep,
                       margin + vstep / 2 + 10,
                       size=8,
                       alignment='middle', anchor='left', text='Change from {}: {}'.format(last_date, txt))
        '''
        # Add the horizontal header label; it is at the very top of the svg and
        # covers the right 16 columns, with centered text
        graph.add_text(margin + hstep * (cols - (cols - 1) / 2),
                       margin + vstep * 0.5, size=13,
                       alignment='middle', text='End of Year Total Wins as Projected by {}'.format(method.upper()))

        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5, alignment='middle', size=13, text='Date')
        graph.add_text(margin + hstep * 1.5, margin + vstep * 1.5, alignment='middle', size=13, text='SP+')

        # Make the color-coded body of the table
        for i in range(0, rows - 1):
            # find the max and min in this week to determine color of cell
            # The rows can be color coded by giving scaling to the maximum likelihood within the week (relative)
            # or by absolute likelihood (max=1.0). Default is relative.
            if absolute:
                upper, lower = 1, 0
            else:
                upper, lower = max(win_probs[i][2]), min(win_probs[i][2])

            for j in range(0, len(win_probs)):
                # where wins <= games played, make the table
                if j < len(win_probs[i][2]):
                    if absolute:
                        r, g, b = Utils.gradient_color(0, 1, win_probs[i][2][j], scale=scale,
                                                       primaryColor=self.primary_color,
                                                       secondaryColor=self.secondary_color)
                    else:
                        r, g, b = Utils.gradient_color(lower, upper, win_probs[i][2][j], scale=scale,
                                                       primaryColor=self.primary_color,
                                                       secondaryColor=self.secondary_color)

                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (2 + j), margin + vstep * (2 + i), hstep, vstep, color='none',
                                   fill=(r, g, b))

                    # Should the text be white or black?
                    text_color = Utils.get_text_contrast_color(r, g, b)

                    graph.add_text(margin + hstep * (2.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   alignment='middle', color=text_color,
                                   text=str(round(100 * win_probs[i][2][j], 1)) + '%')

            j = width
            new_xw = Team.expected_wins(win_probs[i][2])
            # What's the win expectation?
            graph.add_text(margin + hstep * (2.5 + j), margin + vstep * (2.5 + i) - 2, alignment='middle',
                           color=(0, 0, 0), size=13,
                           text=round(new_xw, 1))

        for j in range(0, width):
            if j != 1:
                txt = 'Wins'
            else:
                txt = 'Win'
            # Add the column label
            graph.add_text(margin + hstep * (2.5 + j), margin + vstep * 1.5 - 7, alignment='middle', size=13,
                           text=j)
            graph.add_text(margin + hstep * (2.5 + j),
                           margin + vstep * 1.5 + 7,
                           size=13,
                           alignment='middle',
                           text=txt)

        graph.add_text(margin + hstep * (2.5 + width),
                       margin + vstep * 1.5 - 7,
                       size=11,
                       alignment='middle',
                       text='Expected')
        graph.add_text(margin + hstep * (2.5 + width),
                       margin + vstep * 1.5 + 7,
                       size=11,
                       alignment='middle',
                       text='Wins')

        for i in range(2, rows + 1):
            # add the horizontal lines between the rows
            graph.add_line(x1=margin, y1=margin + vstep * i, x2=margin + hstep * cols, y2=vstep * i + margin)
        for j in range(1, cols):
            # add the vertical lines between the columns
            graph.add_line(x1=margin + hstep * j, y1=margin + vstep, x2=margin + hstep * j,
                           y2=vstep * (rows + 1) + margin)

        for i in range(0, rows - 1):
            graph.add_text(margin + hstep * 0.5, margin + vstep * (2.5 + i), alignment='middle', size=13,
                           text='/'.join(win_probs[i][0].split('-')[1:]))

            # Add the row week label
            graph.add_text(margin + hstep * 1.5, margin + vstep * (2.5 + i), alignment='middle', size=13,
                           text=win_probs[i][1])

        # Draw the outline box for the table
        graph.add_rect(margin, margin + vstep, hstep * cols, vstep * (rows), fill='none', stroke_width=2)

        # Draw the outline box for the win total sub-table
        graph.add_rect(margin + hstep * 2, margin + vstep, hstep * (cols - 3), vstep * (rows), fill='none',
                       stroke_width=2)

        # Draw the outline box for the column headers
        graph.add_rect(margin, margin + vstep, hstep * cols, vstep, fill='none', stroke_width=2)

        # Draw the outline box for the win total header label
        graph.add_rect(margin + hstep * 2, margin, hstep * (cols - 3), vstep, fill='none', stroke_width=2)

        graph.write_file()

    def write_win_probability_csv(self, file='out'):
        record = self.project_win_totals()
        with open("{}.csv".format(file), 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(record)
