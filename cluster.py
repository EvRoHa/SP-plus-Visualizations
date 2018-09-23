import csv
import os
from datetime import datetime

from graph import Graph
from team import Team
from utils import Utils


class Cluster:
    # A cluster is just a group of teams, not necessarily any particular conference or division
    def __init__(self, schedule, teams):
        self.teams = [Team(name=x, schedule=schedule) for x in schedule if x in teams]
        self.schedule = self.teams[0].schedule

    def get_avg_spplus(self, lower, upper):
        sp = []

        for team in self.schedule:
            date = max(datetime.strptime(dt, '%Y-%m-%d') for dt in self.schedule[team]['sp+'].keys()).strftime(
                '%Y-%m-%d')
            sp.append(self.schedule[team]['sp+'][date])
        sp.sort(reverse=True)
        if upper == -1:
            return sum(sp[lower - 1:upper]) / (len(sp) - lower + 1)
        else:
            return sum(sp[lower:upper]) / (upper - lower)

    def get_record_array(self, week=None, order='winexp'):
        # get the records for the final week for each team
        record = []

        for t in self.teams:
            record.append([t, t.project_win_totals(week=week)[-1], t.project_win_totals(week=week - 1)[-1]])

        if order == 'winexp':
            # sort teams by their weighted average number of wins
            record.sort(key=lambda x: sum([x[1][z] * z for z in range(len(x[1]))]), reverse=True)
        elif order == 'sp+':
            record.sort(key=lambda x: x[0].latest_spplus, reverse=True)
        return record

    def make_schedule_ranking_graph(self, file=None, week=None, hstep=50, vstep=50, margin=5, logowidth=40,
                                    absolute=False, old=None, method='sp+', logoheight=40, scale='red-green',
                                    record=None, spplus='top25'):
        date = datetime.now()
        if not isinstance(spplus, int):
            if spplus.lower()[0:3] == 'top':
                try:
                    upper = int(spplus[3:])
                except ValueError:
                    upper = 25
                x = self.get_avg_spplus(0, upper)
                txt = 'average SP+ of top {}'.format(upper)
                stxt = 'sp+ {}'.format(round(x, 1))
            elif spplus.lower()[0:3] == 'bottom':
                try:
                    lower = int(spplus[3:])
                except ValueError:
                    lower = 25
                x = self.get_avg_spplus(lower, -1)
                txt = 'average SP+ of bottom {}'.format(lower)
                stxt = 'sp+ {}'.format(round(x, 1))
            elif spplus == 'average':
                x = self.get_avg_spplus(1, -1)
                txt = 'average SP+ of all FBS'
                stxt = 'sp+ {}'.format(round(x, 1))
            else:
                x = 0.0
                txt = 'spplus 0'
        else:
            x = spplus
            txt = 'SP+ {}'.format(round(spplus, 1))
            stxt = None

        record = self.rank_schedules(spplus=x)

        if not file:
            file = 'Strength of Schedule using {}'.format(txt)

        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {}.svg'.format(file, scale))
        if not old:
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 1
        else:
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 2

        graph = Graph(path=path, width=hstep * cols + 2 * margin, height=vstep * rows + 2 * margin)

        # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
        if stxt:
            offset = 8
            graph.add_text(margin + hstep * (cols + 1) / 2, margin + vstep * 0.5 + offset, size=13,
                           alignment='middle', text='({})'.format(stxt))
        else:
            offset = 0
        graph.add_text(margin + hstep * (cols + 1) / 2, margin + vstep * 0.5 - offset, size=13, alignment='middle',
                       text='Strength of Schedule as projected by {} ordered by {}'.format(method.upper(), txt))

        foo = []
        for i in range(len(record)):
            foo.append(sum([x * record[i][1][x] for x in range(len(record[i][1]))]))

        lower = min(foo)
        upper = max(foo)
        # Add column labels for the Team Name
        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5 - 8, alignment='middle', size=10, text='Team')
        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5 + 8, alignment='middle', size=10, text='Schedule')

        # This set of loops fills in the body of the table
        for i in range(0, rows - 2):
            # Add the team logo
            graph.add_image(margin + (hstep - logowidth) / 2,
                            vstep * (2 + i) + margin + (vstep - logoheight) / 2,
                            logowidth,
                            logoheight,
                            record[i][0].logo_URI)

            # Add the rank in the upper left of the logo box
            graph.add_text(2.5 * margin, vstep * (2 + i) + 2.5 * margin, alignment='middle', size=8, text=i + 1)

            team = record[i][0].name

            cur = x
            win_probabilities = []
            for k in range(len(self.schedule[team]['schedule'])):
                # Get the opponent S&P+ value
                opp_sp = self.schedule[self.schedule[team]['schedule'][k]['opponent']]['sp+']
                # Use the most recent S&P+ values prior to the specified date
                # Note there might be a misalignment between the S&P+ value dates for different teams, especially FCS teams
                best_match = max(
                    datetime.strptime(dt, '%Y-%m-%d') for dt in opp_sp.keys() if
                    datetime.strptime(dt, '%Y-%m-%d') <= date).strftime('%Y-%m-%d')
                osp = opp_sp[best_match]
                # Who has the 2.5 point home field advantage?
                loc = self.schedule[team]['schedule'][k]['home-away']
                # Calculate the win probability and record it
                win_probabilities.append(Utils.calculate_win_prob_from_spplus(cur, osp, loc))
            for j in range(0, cols - 1):
                if i == 0:
                    if j == cols - 2:
                        # Add the column label
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 - 10,
                                       size=10,
                                       alignment='middle',
                                       text='Schedule')
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5,
                                       size=10,
                                       alignment='middle',
                                       text='Expected')
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 + 10,
                                       size=10,
                                       alignment='middle',
                                       text='Wins')
                    elif j <= len(record[i][1]):
                        # Add the column label
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 - 7,
                                       size=13,
                                       alignment='middle',
                                       text='Opp.')
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 + 7,
                                       size=13,
                                       alignment='middle',
                                       text=j + 1)

                if j < len(win_probabilities):
                    r, g, b = Utils.gradient_color(0, 1, win_probabilities[j], scale=scale)

                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, color='none',
                                   fill=(r, g, b))
                    # Add the opponent logo
                    opponent = self.schedule[team]['schedule'][j]['opponent']
                    graph.add_image(margin + hstep * (2 + j) - (hstep + logowidth * 0.8) / 2,
                                    vstep * (2 + i) + margin + (vstep - logoheight * 0.8) / 2,
                                    logowidth * 0.8,
                                    logoheight * 0.8,
                                    self.schedule[opponent]['logoURI'])

                    # Should the text be white or black?
                    text_color = Utils.get_text_contrast_color(r, g, b)

                    # Write the probability in the box
                    graph.add_text(margin + hstep * (1 + j) + 3,
                                   2 * margin + vstep * (2 + i) + 3,
                                   alignment='middle', anchor='left', size=8,
                                   color=tuple(text_color),
                                   text=str(round(100 * win_probabilities[j], 1)) + '%')

                    # Add the cumulative probability text
                    graph.add_text(0.8 * margin + hstep * (2 + j),
                                   vstep * (3 + i),
                                   alignment='middle', anchor='end', size=8,
                                   color=tuple(text_color),
                                   text=str(round(abs(100 * (1 - sum(record[i][1][x] for x in range(0, j)))), 1)) + '%')

                elif j == cols - 2:
                    # Calculate the win expectation
                    xw = sum(x * record[i][1][x] for x in range(len(record[i][1])))

                    r, g, b = Utils.gradient_color(lower, upper, xw, scale=scale)

                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep, color='none',
                                   fill=(r, g, b))

                    # Should the text be white or black?
                    text_color = Utils.get_text_contrast_color(r, g, b)

                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i),
                                   size=13,
                                   alignment='middle',
                                   color=tuple(text_color),
                                   text=round(xw, 3))

                else:
                    # Draw a gray box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep,
                                   color='none', fill=(150, 150, 150))

        # This set of loops draws the grid over the table.
        for i in range(2, rows):
            for j in range(1, cols):
                # add the vertical lines between the columns
                graph.add_line(x1=margin + hstep * j, y1=margin + vstep, x2=margin + hstep * j,
                               y2=margin + vstep * rows)

            # add the horizontal lines between the rows
            graph.add_line(x1=margin, y1=margin + vstep * i, x2=margin + hstep * cols,
                           y2=margin + vstep * i)

        # Draw the outline box for the table
        graph.add_rect(margin, margin + vstep, hstep * cols, vstep * (rows - 1), color=(0, 0, 0), fill='none',
                       stroke_width=2)

        # Draw the outline box for the win total sub-table
        graph.add_rect(margin + hstep, margin + vstep, hstep * (cols - 1), vstep * (rows - 1), color=(0, 0, 0),
                       fill='none', stroke_width=2)

        # Draw the outline box for the column headers
        graph.add_rect(margin, margin + vstep, hstep * cols, vstep, color=(0, 0, 0), fill='none', stroke_width=2)

        # Draw the outline box for the win total header label
        graph.add_rect(margin + hstep, margin, hstep * (cols - 2), 2 * vstep, color=(0, 0, 0), fill='none',
                       stroke_width=2)
        graph.write_file()

    def make_standings_projection_graph(self, file='out', week=None, hstep=50, vstep=50, margin=5, logowidth=40,
                                        old=None, method='sp+', logoheight=40, absolute=False, scale='red-green',
                                        record=None, order='winexp'):
        if not record:
            # get the records for the final week for each team
            record = self.get_record_array(week, order)

        if not os.path.exists(".\svg output\{} - {}".format(method, scale)):
            os.makedirs(".\svg output\{} - {}".format(method, scale))
        path = os.path.join(".\svg output\{} - {}".format(method, scale),
                            '{} - {} - {} using {}.svg'.format(file, method, scale, order))

        if not old:
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 1
        else:
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 2

        graph = Graph(path=path, width=hstep * cols + 2 * margin, height=vstep * rows + 2 * margin)

        # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
        graph.add_text(margin + hstep * (cols + 1) / 2, margin + vstep * 0.5 - 4, size=13, alignment='middle',
                       text='Total Wins as projected by {} ordered by {}'.format(method.upper(), order.upper()))

        if not week or week == 0:
            first_week = 0
        else:
            first_week = week - 1

        # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
        if first_week > 0:
            graph.add_text(margin + hstep * (cols + 1) / 2,
                           margin + vstep * 0.5 + 9,
                           size=13, alignment='middle',
                           text='(change after week {} games)'.format(first_week))

        # Add column labels for the Team Name
        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5, alignment='middle', size=13, text='Team')

        # This set of loops fills in the body of the table
        for i in range(0, rows - 2):
            # Add the team logo
            graph.add_image(margin + (hstep - logowidth) / 2,
                            vstep * (2 + i) + margin + (vstep - logoheight) / 2,
                            logowidth,
                            logoheight,
                            record[i][0].logo_URI)

            # Add the rank in the upper left of the logo box
            graph.add_text(2.5 * margin, vstep * (2 + i) + 2.5 * margin, alignment='middle', size=8, text=i + 1)

            # find the max and min in this week to determine color of cell
            if absolute:
                upper, lower = 1, 0
            else:
                upper, lower = max(record[i][1]), min(record[i][1])

            for j in range(0, cols - 1):
                if i == 0:
                    if j == cols - 2:
                        if old:
                            # Add the column label
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5 - 10,
                                           size=10,
                                           alignment='middle',
                                           text='Expected')
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5,
                                           size=10,
                                           alignment='middle',
                                           text='Wins')
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5 + 10,
                                           alignment='middle',
                                           size=10,
                                           text='(Change)')
                    elif j <= len(record[i][1]):
                        if j != 1:
                            txt = 'Wins'
                        else:
                            txt = 'Win'
                        # Add the column label
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 - 7,
                                       size=13,
                                       alignment='middle',
                                       text=j)
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 + 7,
                                       size=13,
                                       alignment='middle',
                                       text=txt)

                if j < len(record[i][1]):
                    if absolute:
                        r, g, b = Utils.gradient_color(0, 1, record[i][1][j], scale=scale,
                                                       primaryColor=record[i][0].primary_color,
                                                       secondaryColor=record[i][0].secondary_color)
                    else:
                        r, g, b = Utils.gradient_color(lower, upper, record[i][1][j], scale=scale,
                                                       primaryColor=record[i][0].primary_color,
                                                       secondaryColor=record[i][0].secondary_color)

                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep,
                                   color='none', fill=(r, g, b))

                    # Should the text be white or black?
                    text_color = Utils.get_text_contrast_color(r, g, b)

                    # Write the probability in the box
                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   alignment='middle',
                                   color=tuple(text_color),
                                   text=str(round(100 * record[i][1][j], 1)) + '%')

                    # Add the cumulative probability text
                    graph.add_text(0.8 * margin + hstep * (2 + j),
                                   vstep * (3 + i),
                                   alignment='middle', anchor='end', size=8,
                                   color=tuple(text_color),
                                   text=str(round(abs(100 * (1 - sum(record[i][1][x] for x in range(0, j)))), 1)) + '%')

                    if old:
                        diff = round(100 * (record[i][1][j] - record[i][2][j]), 1)
                        if diff > 0:
                            txt = '(+{})%'.format(diff)
                        elif diff < 0:
                            txt = '(' + str(diff) + '%)'
                        else:
                            txt = '(+' + str(diff) + '%)'

                        # Write the probability change in the box
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * (2.5 + i) + 8,
                                       size=10, alignment='middle',
                                       color=tuple(text_color),
                                       text=txt)

                elif j == cols - 2 and old:
                    # Calculate the win expectation
                    old_xw = sum(x * record[i][2][x] for x in range(len(record[i][2])))
                    new_xw = sum(x * record[i][1][x] for x in range(len(record[i][1])))
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

                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   size=13,
                                   text=round(new_xw, 1))

                    # How did the win expectation change?
                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) + 8,
                                   alignment='middle',
                                   size=10,
                                   color=(r, g, b),
                                   weight=weight,
                                   text=txt)
                else:
                    # Draw a gray box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep,
                                   color='none', fill=(150, 150, 150))

        # This set of loops draws the grid over the table.
        for i in range(2, rows):
            for j in range(1, cols):
                # add the vertical lines between the columns
                graph.add_line(x1=margin + hstep * j, y1=margin + vstep, x2=margin + hstep * j,
                               y2=margin + vstep * rows)

            # add the horizontal lines between the rows
            graph.add_line(x1=margin, y1=margin + vstep * i, x2=margin + hstep * cols,
                           y2=margin + vstep * i)

            # Draw the outline box for the table
            graph.add_rect(margin, margin + vstep, hstep * cols, vstep * (rows - 1), color=(0, 0, 0), fill='none',
                           stroke_width=2)

            # Draw the outline box for the win total sub-table
            graph.add_rect(margin + hstep, margin + vstep, hstep * (cols - 1), vstep * (rows - 1), color=(0, 0, 0),
                           fill='none', stroke_width=2)

            # Draw the outline box for the column headers
            graph.add_rect(margin, margin + vstep, hstep * cols, vstep, color=(0, 0, 0), fill='none', stroke_width=2)

            # Draw the outline box for the win total header label
            graph.add_rect(margin + hstep, margin, hstep * (cols - 2), vstep, color=(0, 0, 0), fill='none',
                           stroke_width=2)
            graph.write_file()

    def rank_schedules(self, file='out', week=None, hstep=40, vstep=40, margin=5, logowidth=30,
                       method='sp+', logoheight=30, absolute=False, scale='red-green', spplus=0.0, txtoutput=False):
        record = []

        # make sure the week is valid
        if (not week) or (week < 1) or (week > max([len(x.win_probabilities[week]) for x in self.teams])):
            week = -1

        # recalculate the win probabilities as though the team were average (S&P+ = 0.0)
        modified_teams = self.teams
        for team in modified_teams:
            for x in team.spplus:
                cur = spplus
                team.win_probabilities[x] = []
                date = datetime.strptime(x, "%Y-%m-%d")
                for i in range(len(team.schedule[team.name]['schedule'])):
                    # Get the opponent S&P+ value
                    opp_sp = team.schedule[team.schedule[team.name]['schedule'][i]['opponent']]['sp+']
                    # Use the most recent S&P+ values prior to the specified date
                    # Note there might be a misalignment between the S&P+ value dates for different teams, especially FCS teams
                    best_match = max(
                        datetime.strptime(dt, '%Y-%m-%d') for dt in opp_sp.keys() if
                        datetime.strptime(dt, '%Y-%m-%d') <= date).strftime('%Y-%m-%d')
                    osp = opp_sp[best_match]
                    # Who has the 2.5 point home field advantage?
                    loc = team.schedule[team.name]['schedule'][i]['home-away']
                    # Calculate the win probability and record it
                    team.win_probabilities[x].append(Utils.calculate_win_prob_from_spplus(cur, osp, loc))

        # sort teams by their weighted average number of wins and division
        ordered_teams = sorted([[x, x.project_win_totals()[week]] for x in modified_teams],
                               key=lambda y: 12 * sum([y[1][z] * z for z in range(len(y[1]))]) / len(y[1]))
        record.extend(ordered_teams)

        if txtoutput:
            with open(file + '.csv', 'w+', newline='') as outfile:
                csvwriter = csv.writer(outfile)

                base = 12 * sum(ordered_teams[0][1][i] * i for i in range(len(ordered_teams[0][1]))) / len(
                    ordered_teams[0][1])

                conferences = {}
                rank = 1
                for x in ordered_teams:
                    x.append(12 * round(sum(x[1][i] * i for i in range(len(x[1]))) / len(ordered_teams[0][1]), 3))
                    if x[0].conference not in conferences.keys():
                        conferences[x[0].conference] = {'count': 1, 'positions': rank, 'xw': x[2]}
                    else:
                        conferences[x[0].conference]['count'] += 1
                        conferences[x[0].conference]['positions'] += rank
                        conferences[x[0].conference]['xw'] += x[2]
                    rank += 1

                csvwriter.writerow(['Name', 'Mean Rank', 'Mean Expected Wins', 'Mean Advantage'])
                rank = 1
                for c in sorted(conferences.items(), key=lambda y: y[1]['positions'] / y[1]['count']):
                    csvwriter.writerow([rank.__str__() + ". " + c[0].title(),
                                        c[1]['positions'] / c[1]['count'],
                                        c[1]['xw'] / c[1]['count'],
                                        c[1]['xw'] / c[1]['count'] - base])
                    rank += 1
                csvwriter.writerow([])

                csvwriter.writerow(['Name', 'Conference', 'Expected Wins', 'Advantage'])
                rank = 1
                for x in ordered_teams:
                    csvwriter.writerow(
                        [x[0].name.title(), x[0].conference.title(), x[2], x[2] - base])
                    rank += 1

        return record
